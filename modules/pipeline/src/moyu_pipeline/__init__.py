"""Pack orchestration: time plan, metadata patches, ZIP and manifest."""

import datetime as dt
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass

from moyu_archive_zip import ArchiveError, ArchiveWriter, verify_archive
from moyu_core_time import SourceTime, TimeError, plan_times
from moyu_media_metadata import (
    MetadataError,
    build_metadata_patches,
    iter_patched_chunks,
    materialize_metadata,
    patch_to_dict,
)

__all__ = [
    "PackError",
    "PackInput",
    "pack",
    "resolve_offset",
]


class PackError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PackInput:
    source: str
    arcname: str


def resolve_offset(timezone, target_epoch):
    if timezone is None:
        return 0
    offset = target_epoch
    zone = dt.timezone.utc if timezone in ("UTC", "Etc/UTC") else None
    if zone is None:
        try:
            from zoneinfo import ZoneInfo

            zone = ZoneInfo(timezone)
        except Exception as exc:
            raise PackError("invalid_timezone", f"无法解析时区: {timezone}") from exc
    delta = dt.datetime.fromtimestamp(offset, tz=zone).utcoffset()
    if delta is None:
        raise PackError("invalid_timezone", f"时区没有 UTC offset: {timezone}")
    return int(delta.total_seconds())


def _entry_metadata(info):
    fields = info.records or [
        patch_to_dict(patch)
        for patch in info.patches
        if not patch.field.endswith("CRC")
    ]
    if info.requires_materialize:
        mode = "materialize"
    elif info.patches:
        mode = "patches"
    else:
        mode = "none"
    return {
        "format": info.format,
        "mode": mode,
        "patches": len(info.patches),
        "fields": fields,
        "notes": list(info.notes),
        "strict_problems": list(info.strict_problems),
    }


def _write_manifest(path, data):
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".moyu-manifest-", suffix=".part", dir=directory)
    os.close(fd)
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp, path)
        tmp = None
    except OSError as exc:
        raise PackError("manifest_write_failed", f"写入 manifest 失败: {exc}") from exc
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def pack(
    inputs,
    target_epoch,
    output,
    timezone="UTC",
    utc_offset_seconds=None,
    compression="store",
    strict_metadata=False,
    force=False,
    verify=True,
    manifest_path=None,
    chunk_size=1024 * 1024,
):
    if not inputs:
        raise PackError("empty", "没有输入文件")
    names = set()
    for item in inputs:
        if item.arcname in names:
            raise PackError("duplicate_arcname", f"重复的归档路径: {item.arcname}")
        names.add(item.arcname)

    sources = []
    stats = {}
    for item in inputs:
        try:
            stat = os.stat(item.source)
        except OSError as exc:
            raise PackError("source_missing", f"无法读取源文件 {item.source}: {exc}") from exc
        stats[item.arcname] = (stat.st_size, stat.st_mtime_ns)
        sources.append(SourceTime(item.arcname, stat.st_mtime_ns))

    offset = (
        resolve_offset(timezone, target_epoch)
        if utc_offset_seconds is None
        else int(utc_offset_seconds)
    )
    try:
        plan = plan_times(sources, target_epoch, offset)
    except TimeError as exc:
        raise PackError(exc.code, str(exc)) from exc

    if timezone in (None, "UTC", "Etc/UTC"):
        tz = dt.timezone.utc
    else:
        try:
            from zoneinfo import ZoneInfo

            tz = ZoneInfo(timezone)
        except Exception as exc:
            raise PackError("invalid_timezone", f"无法解析时区: {timezone}") from exc

    outdir = os.path.dirname(os.path.abspath(output)) or "."
    materialized = []
    entries = []
    try:
        writer = ArchiveWriter(
            output,
            compression=compression,
            force=force,
            verify=False,
            timezone=timezone or "UTC",
            chunk_size=chunk_size,
        )
        try:
            for item, planned in zip(inputs, plan.entries):
                try:
                    info = build_metadata_patches(
                        item.source, planned.target_epoch, tz
                    )
                except MetadataError as exc:
                    raise PackError(
                        "metadata_failed", f"元数据解析失败: {item.source}: {exc}"
                    ) from exc
                if strict_metadata and info.strict_problems:
                    raise PackError(
                        "metadata_strict",
                        f"严格元数据检查失败: {item.source}: "
                        + "; ".join(info.strict_problems),
                    )
                metadata = _entry_metadata(info)
                size, mtime_ns = stats[item.arcname]
                if info.requires_materialize:
                    try:
                        produced = materialize_metadata(
                            item.source, info, planned.target_epoch, tz, outdir
                        )
                    except MetadataError as exc:
                        raise PackError(
                            "metadata_failed",
                            f"元数据重建失败: {item.source}: {exc}",
                        ) from exc
                    if not produced:
                        raise PackError(
                            "metadata_failed", f"元数据重建未生成文件: {item.source}"
                        )
                    materialized.append(produced)
                    with open(produced, "rb") as stream:
                        writer.add_entry(
                            item.arcname,
                            planned.dos.as_tuple(),
                            stream,
                            size=os.path.getsize(produced),
                        )
                elif info.patches:
                    writer.add_entry(
                        item.arcname,
                        planned.dos.as_tuple(),
                        iter_patched_chunks(item.source, info.patches, chunk_size),
                        size=size,
                    )
                else:
                    writer.add_file(
                        item.arcname, planned.dos.as_tuple(), item.source
                    )
                after = os.stat(item.source)
                if (after.st_size, after.st_mtime_ns) != (size, mtime_ns):
                    raise PackError(
                        "source_changed", f"打包过程中源文件发生变化: {item.source}"
                    )
                entries.append(
                    {
                        "arcname": item.arcname,
                        "source": os.path.abspath(item.source),
                        "source_mtime_ns": planned.source_mtime_ns,
                        "target_epoch": planned.target_epoch,
                        "dos": list(planned.dos.as_tuple()),
                        "metadata": metadata,
                    }
                )
        except Exception:
            writer.abort()
            raise
        summary = writer.finalize()
    finally:
        for produced in materialized:
            try:
                os.unlink(produced)
            except OSError:
                pass

    expected = {
        entry["arcname"]: {"dos": entry["dos"], "target_epoch": entry["target_epoch"]}
        for entry in entries
    }
    result = verify_archive(
        output,
        expected=expected,
        timezone=timezone or "UTC",
        strict=True,
        require_store=compression == "store",
        check_crc=True,
    )
    if verify and not result["ok"]:
        raise PackError(
            "verify_failed", "归档校验失败: " + "; ".join(result["problems"][:5])
        )

    manifest = {
        "version": 1,
        "archive": os.path.abspath(output),
        "archive_sha256": _sha256(output),
        "archive_bytes": os.path.getsize(output),
        "timezone": timezone or "UTC",
        "utc_offset_seconds": offset,
        "target_epoch": plan.target_epoch,
        "delta_ns": plan.delta_ns,
        "compression": compression,
        "entries": entries,
    }
    if manifest_path:
        _write_manifest(manifest_path, manifest)
    return {
        "summary": summary.to_dict(),
        "manifest": manifest,
        "verify": result,
    }