import datetime as dt
import json
import os
import shutil
import stat
import struct
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass

DEFAULT_TZ = "Asia/Shanghai"
DEFAULT_CHUNK = 1024 * 1024
TIME_EXTRA_IDS = {0x5455, 0x000A, 0x5855, 0x000D}
ZIP64_EXTRA_ID = 0x0001
UNICODE_EXTRA_IDS = {0x7075, 0x6375}
DOS_MIN_YEAR = 1980
DOS_MAX_YEAR = 2107


class MoyuError(Exception):
    pass


@dataclass
class EntryPlan:
    source: str
    arcname: str
    mode: int
    size: int
    source_mtime_ns: int
    target_epoch: int
    dos: tuple


def resolve_timezone(name):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception as exc:
        if name in ("Asia/Shanghai", "PRC", "UTC+8"):
            return dt.timezone(dt.timedelta(hours=8), name)
        if name in ("UTC", "Etc/UTC"):
            return dt.timezone.utc
        raise MoyuError(f"无法解析时区: {name}") from exc


def dos_datetime(epoch, tz):
    value = dt.datetime.fromtimestamp(epoch, tz=tz)
    return (
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second - (value.second % 2),
    )


def epoch_from_dos(value, tz):
    return int(
        dt.datetime(
            value[0], value[1], value[2], value[3], value[4], value[5], tzinfo=tz
        ).timestamp()
    )


def encode_dos(value):
    year, month, day, hour, minute, second = value
    if not (DOS_MIN_YEAR <= year <= DOS_MAX_YEAR):
        raise MoyuError(f"DOS 时间超出 {DOS_MIN_YEAR}-{DOS_MAX_YEAR}: {value}")
    dos_date = ((year - DOS_MIN_YEAR) << 9) | (month << 5) | day
    dos_time = (hour << 11) | (minute << 5) | (second // 2)
    return dos_time, dos_date


def decode_dos(dos_time, dos_date):
    second = (dos_time & 0x1F) * 2
    minute = (dos_time >> 5) & 0x3F
    hour = (dos_time >> 11) & 0x1F
    day = dos_date & 0x1F
    month = (dos_date >> 5) & 0x0F
    year = ((dos_date >> 9) & 0x7F) + DOS_MIN_YEAR
    return (year, month, day, hour, minute, second)


def format_epoch(epoch, tz):
    return dt.datetime.fromtimestamp(epoch, tz=tz).strftime("%Y-%m-%d %H:%M:%S %z")


def human_size(size):
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"


def parse_size(value):
    text = value.strip().lower()
    if not text:
        raise MoyuError("大小不能为空")
    units = {
        "": 1,
        "b": 1,
        "k": 1024,
        "kb": 1024,
        "kib": 1024,
        "m": 1024 ** 2,
        "mb": 1024 ** 2,
        "mib": 1024 ** 2,
        "g": 1024 ** 3,
        "gb": 1024 ** 3,
        "gib": 1024 ** 3,
    }
    for suffix in sorted(units, key=len, reverse=True):
        if suffix and text.endswith(suffix):
            number = text[: -len(suffix)].strip()
            break
    else:
        number = text
        suffix = ""
    try:
        result = int(float(number) * units[suffix])
    except (ValueError, KeyError, OverflowError) as exc:
        raise MoyuError(f"无法解析大小: {value}") from exc
    if result <= 0:
        raise MoyuError(f"大小必须大于 0: {value}")
    return result


def parse_extra(extra):
    result = []
    pos = 0
    while pos < len(extra):
        if pos + 4 > len(extra):
            raise MoyuError("extra field 头部不完整")
        header_id, size = struct.unpack_from("<HH", extra, pos)
        end = pos + 4 + size
        if end > len(extra):
            raise MoyuError("extra field 数据不完整")
        result.append((header_id, extra[pos + 4 : end]))
        pos = end
    return result


def check_extra_fields(
    fields,
    location,
    problems,
    extra_ids,
    strict=True,
    allow_unicode_extra=False,
    allow_mtime_ut=False,
):
    for header_id, data in fields:
        extra_ids.add(header_id)
        if header_id == ZIP64_EXTRA_ID:
            continue
        if header_id == 0x5455:
            flags = data[0] if data else 0
            if allow_mtime_ut and flags == 0x01 and len(data) == 5:
                continue
            problems.append(f"{location}: 含 UT 时间扩展字段 0x5455")
            continue
        if header_id in TIME_EXTRA_IDS:
            problems.append(f"{location}: 含时间扩展字段 0x{header_id:04x}")
            continue
        if header_id in UNICODE_EXTRA_IDS and allow_unicode_extra:
            continue
        if strict:
            problems.append(f"{location}: 含未允许的扩展字段 0x{header_id:04x}")


def collect_inputs(
    inputs, prefix="", follow_symlinks=False, output=None, exclude=None
):
    excluded = {os.path.abspath(item) for item in (exclude or []) if item}
    if output:
        excluded.add(os.path.abspath(output))
    result = []
    for item in inputs:
        path = os.path.abspath(item)
        if not os.path.exists(path):
            raise MoyuError(f"输入不存在: {item}")
        if os.path.islink(path) and not follow_symlinks:
            print(f"moyu-pack: 跳过符号链接: {item}", file=sys.stderr)
            continue
        if os.path.isdir(path):
            root = os.path.basename(os.path.normpath(path)) or "root"
            for dirpath, dirnames, filenames in os.walk(
                path, followlinks=follow_symlinks
            ):
                dirnames.sort()
                filenames.sort()
                for name in filenames:
                    src = os.path.join(dirpath, name)
                    if os.path.abspath(src) in excluded:
                        continue
                    if os.path.islink(src) and not follow_symlinks:
                        print(f"moyu-pack: 跳过符号链接: {src}", file=sys.stderr)
                        continue
                    if not os.path.isfile(src):
                        continue
                    rel = os.path.relpath(src, path)
                    arcname = "/".join([root, *rel.split(os.sep)])
                    result.append((src, arcname))
        elif os.path.isfile(path):
            if path in excluded:
                continue
            result.append((path, os.path.basename(path)))
        else:
            raise MoyuError(f"不是普通文件或目录: {item}")

    if prefix:
        clean = prefix.strip("/").replace("\\", "/")
        parts = [part for part in clean.split("/") if part]
        if any(part in (".", "..") for part in parts):
            raise MoyuError("prefix 不能包含 . 或 ..")
        if parts:
            result = [(src, "/".join([*parts, arc])) for src, arc in result]

    if not result:
        raise MoyuError("没有可打包的文件")

    seen = {}
    for src, arcname in result:
        if "\\" in arcname:
            raise MoyuError(f"归档路径包含反斜杠: {arcname}")
        if arcname.startswith("/") or ".." in arcname.split("/"):
            raise MoyuError(f"不安全的归档路径: {arcname}")
        if arcname in seen:
            raise MoyuError(f"归档路径冲突: {arcname} ({seen[arcname]} 与 {src})")
        seen[arcname] = src

    result.sort(key=lambda pair: pair[1])
    return result


def plan_pack(
    inputs,
    target="now",
    tz_name=DEFAULT_TZ,
    prefix="",
    follow_symlinks=False,
    output=None,
    exclude=None,
):
    tz = resolve_timezone(tz_name)
    pairs = collect_inputs(
        inputs,
        prefix=prefix,
        follow_symlinks=follow_symlinks,
        output=output,
        exclude=exclude,
    )
    entries = []
    for src, arcname in pairs:
        try:
            st = os.stat(src)
        except OSError as exc:
            raise MoyuError(f"无法读取文件: {src}: {exc}") from exc
        if not stat.S_ISREG(st.st_mode):
            raise MoyuError(f"不是普通文件: {src}")
        entries.append((src, arcname, st))

    max_mtime_ns = max(st.st_mtime_ns for _, _, st in entries)
    if target == "now":
        target_ns = time.time_ns()
    else:
        try:
            value = dt.datetime.strptime(target, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=tz
            )
        except ValueError as exc:
            raise MoyuError("target 格式应为 YYYY-MM-DD HH:MM:SS 或 now") from exc
        target_ns = int(value.timestamp()) * 1_000_000_000

    delta_ns = target_ns - max_mtime_ns
    if delta_ns <= 0:
        raise MoyuError("最新文件时间不早于目标时间，未做调整")

    plans = []
    for src, arcname, st in entries:
        shifted_ns = st.st_mtime_ns + delta_ns
        epoch = shifted_ns // 1_000_000_000
        dos = dos_datetime(epoch, tz)
        encode_dos(dos)
        plans.append(
            EntryPlan(
                source=src,
                arcname=arcname,
                mode=st.st_mode,
                size=st.st_size,
                source_mtime_ns=st.st_mtime_ns,
                target_epoch=epoch,
                dos=dos,
            )
        )
    return plans, tz, target_ns, delta_ns


def write_manifest(path, plans, tz_name, target_ns, delta_ns, output):
    data = {
        "tool": "moyu-pack",
        "tz": tz_name,
        "target_epoch": target_ns // 1_000_000_000,
        "delta_ns": delta_ns,
        "archive": os.path.abspath(output),
        "entries": [
            {
                "arcname": plan.arcname,
                "source": plan.source,
                "source_mtime_ns": plan.source_mtime_ns,
                "target_epoch": plan.target_epoch,
                "dos": list(plan.dos),
            }
            for plan in plans
        ],
    }
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".moyu-manifest-", suffix=".part", dir=directory
    )
    os.close(fd)
    try:
        os.chmod(tmp_path, 0o644)
    except OSError:
        pass
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp_path, path)
        tmp_path = None
    except OSError as exc:
        raise MoyuError(f"写入 manifest 失败: {exc}") from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def write_zip(
    plans,
    output,
    tz_name,
    target_ns,
    delta_ns,
    deflate=False,
    chunk_size=DEFAULT_CHUNK,
    force=False,
    fsync=True,
    manifest_path=None,
    verify=True,
):
    output_abs = os.path.abspath(output)
    outdir = os.path.dirname(output_abs) or "."
    os.makedirs(outdir, exist_ok=True)
    if os.path.isdir(output_abs):
        raise MoyuError(f"输出路径是目录: {output}")
    if os.path.exists(output_abs) and not force:
        raise MoyuError(f"输出已存在，使用 --force 覆盖: {output}")

    total_size = sum(plan.size for plan in plans)
    free = shutil.disk_usage(outdir).free
    required = total_size + 64 * 1024 * 1024
    if free < required:
        raise MoyuError(
            f"磁盘空间不足: 需要约 {human_size(required)}, 可用 {human_size(free)}"
        )

    fd, tmp_path = tempfile.mkstemp(prefix=".moyu-", suffix=".part", dir=outdir)
    os.close(fd)
    try:
        os.chmod(tmp_path, 0o644)
    except OSError:
        pass
    started = time.monotonic()
    try:
        compression = zipfile.ZIP_DEFLATED if deflate else zipfile.ZIP_STORED
        with open(tmp_path, "wb", buffering=4 * 1024 * 1024) as fp:
            with zipfile.ZipFile(
                fp,
                "w",
                compression=compression,
                allowZip64=True,
                compresslevel=1 if deflate else None,
            ) as zf:
                for plan in plans:
                    zinfo = zipfile.ZipInfo(plan.arcname, date_time=plan.dos)
                    zinfo.compress_type = compression
                    zinfo.create_system = 3
                    zinfo.external_attr = (plan.mode & 0xFFFF) << 16
                    zinfo.extra = b""
                    zinfo.comment = b""
                    if deflate:
                        zinfo._compresslevel = 1
                    force_zip64 = plan.size > zipfile.ZIP64_LIMIT
                    with open(plan.source, "rb") as src, zf.open(
                        zinfo, "w", force_zip64=force_zip64
                    ) as dst:
                        while True:
                            chunk = src.read(chunk_size)
                            if not chunk:
                                break
                            dst.write(chunk)
                    after = os.stat(plan.source)
                    if (
                        after.st_size != plan.size
                        or after.st_mtime_ns != plan.source_mtime_ns
                    ):
                        raise MoyuError(f"打包过程中源文件发生变化: {plan.source}")
            fp.flush()
            if fsync:
                os.fsync(fp.fileno())

        if verify:
            expected = {
                plan.arcname: {
                    "dos": list(plan.dos),
                    "target_epoch": plan.target_epoch,
                }
                for plan in plans
            }
            result = verify_zip(
                tmp_path,
                expected=expected,
                tz_name=tz_name,
                strict=True,
                require_store=not deflate,
            )
            if not result["ok"]:
                raise MoyuError(
                    "打包后校验失败: " + "; ".join(result["problems"][:5])
                )

        os.replace(tmp_path, output_abs)
        tmp_path = None
        if manifest_path:
            write_manifest(manifest_path, plans, tz_name, target_ns, delta_ns, output_abs)
        elapsed = time.monotonic() - started
        return {
            "ok": True,
            "output": output_abs,
            "entries": len(plans),
            "total_bytes": total_size,
            "archive_bytes": os.path.getsize(output_abs),
            "elapsed_sec": elapsed,
            "throughput_bytes_s": total_size / elapsed if elapsed > 0 else 0,
            "tz": tz_name,
            "target_epoch": target_ns // 1_000_000_000,
            "delta_ns": delta_ns,
            "min_epoch": min(plan.target_epoch for plan in plans),
            "max_epoch": max(plan.target_epoch for plan in plans),
            "deflate": bool(deflate),
            "chunk_size": chunk_size,
            "verified": bool(verify),
        }
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise MoyuError(f"写入 ZIP 失败: {exc}") from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def read_local_header(zf, info):
    fp = zf.fp
    fp.seek(info.header_offset)
    header = fp.read(30)
    if len(header) != 30:
        raise MoyuError("本地文件头不完整")
    (
        signature,
        version,
        flags,
        method,
        dos_time,
        dos_date,
        crc,
        compressed_size,
        file_size,
        name_len,
        extra_len,
    ) = struct.unpack("<IHHHHHIIIHH", header)
    if signature != 0x04034B50:
        raise MoyuError("本地文件头签名错误")
    fp.seek(info.header_offset + 30 + name_len)
    extra = fp.read(extra_len)
    if len(extra) != extra_len:
        raise MoyuError("本地文件头 extra 字段不完整")
    return {
        "flags": flags,
        "method": method,
        "dos_time": dos_time,
        "dos_date": dos_date,
        "extra": extra,
    }


def verify_zip(
    path,
    expected=None,
    tz_name=DEFAULT_TZ,
    strict=True,
    allow_unicode_extra=False,
    allow_mtime_ut=False,
    require_store=False,
    check_crc=False,
    no_future=False,
):
    problems = []
    extra_ids = set()
    compression_counts = {}
    epochs = []
    tz = resolve_timezone(tz_name)
    entries = 0
    archive_comment = 0

    try:
        with zipfile.ZipFile(path) as zf:
            archive_comment = len(zf.comment)
            if zf.comment:
                problems.append("归档带有 comment")
            infos = zf.infolist()
            entries = len(infos)
            if not infos:
                problems.append("归档为空")
            names = set()
            for info in infos:
                label = info.filename
                if (
                    not label
                    or label.startswith("/")
                    or label.startswith("\\")
                    or "\\" in label
                    or ".." in label.split("/")
                ):
                    problems.append(f"{label}: 不安全的归档路径")
                if label in names:
                    problems.append(f"{label}: 重复的归档路径")
                names.add(label)

                if info.flag_bits & 0x1:
                    problems.append(f"{label}: 条目被加密")
                if strict and info.flag_bits & 0x8:
                    problems.append(f"{label}: 使用 data descriptor")
                if info.comment:
                    problems.append(f"{label}: 条目带有 comment")

                try:
                    central_fields = parse_extra(info.extra)
                except MoyuError as exc:
                    problems.append(f"{label}: 中央目录 {exc}")
                else:
                    check_extra_fields(
                        central_fields,
                        f"{label} 中央目录",
                        problems,
                        extra_ids,
                        strict,
                        allow_unicode_extra,
                        allow_mtime_ut,
                    )

                try:
                    local = read_local_header(zf, info)
                except MoyuError as exc:
                    problems.append(f"{label}: {exc}")
                else:
                    try:
                        local_fields = parse_extra(local["extra"])
                    except MoyuError as exc:
                        problems.append(f"{label}: 本地文件头 {exc}")
                    else:
                        check_extra_fields(
                            local_fields,
                            f"{label} 本地文件头",
                            problems,
                            extra_ids,
                            strict,
                            allow_unicode_extra,
                            allow_mtime_ut,
                        )
                    try:
                        central_dos = encode_dos(info.date_time)
                    except MoyuError as exc:
                        problems.append(f"{label}: {exc}")
                    else:
                        if (local["dos_time"], local["dos_date"]) != central_dos:
                            problems.append(
                                f"{label}: 本地头与中央目录 DOS 时间不一致"
                            )
                    if local["method"] != info.compress_type:
                        problems.append(
                            f"{label}: 本地头与中央目录压缩方法不一致"
                        )
                    if strict and local["flags"] & 0x1:
                        problems.append(f"{label}: 本地头标记加密")

                try:
                    encode_dos(info.date_time)
                    epoch = epoch_from_dos(info.date_time, tz)
                except (MoyuError, ValueError, OverflowError) as exc:
                    problems.append(f"{label}: 非法 DOS 时间 {info.date_time!r}: {exc}")
                else:
                    epochs.append(epoch)

                compression_counts[info.compress_type] = (
                    compression_counts.get(info.compress_type, 0) + 1
                )
                if require_store and info.compress_type != zipfile.ZIP_STORED:
                    problems.append(f"{label}: 未使用 STORE")

            if expected:
                if isinstance(expected, dict) and "entries" in expected:
                    expected_map = expected["entries"]
                else:
                    expected_map = expected
                if not isinstance(expected_map, (dict, list)):
                    problems.append("manifest 格式错误: entries 类型非法")
                    expected_map = {}
                if isinstance(expected_map, list):
                    try:
                        expected_map = {
                            item["arcname"]: item for item in expected_map
                        }
                    except (KeyError, TypeError):
                        problems.append("manifest 格式错误: entries 缺少 arcname")
                        expected_map = {}
                actual_names = {info.filename for info in infos}
                missing = set(expected_map) - actual_names
                extra_names = actual_names - set(expected_map)
                if missing:
                    problems.append(f"缺少条目: {sorted(missing)[:5]}")
                if extra_names:
                    problems.append(f"多出条目: {sorted(extra_names)[:5]}")
                for info in infos:
                    want = expected_map.get(info.filename)
                    if not want:
                        continue
                    if not isinstance(want, dict):
                        problems.append(f"{info.filename}: manifest 条目格式错误")
                        continue
                    want_dos = want.get("dos")
                    if want_dos is not None:
                        try:
                            if tuple(want_dos) != tuple(info.date_time):
                                problems.append(
                                    f"{info.filename}: DOS 时间不匹配 "
                                    f"{info.date_time} != {tuple(want_dos)}"
                                )
                        except TypeError:
                            problems.append(f"{info.filename}: manifest 中 dos 非法")
                    want_epoch = want.get("target_epoch")
                    if want_epoch is not None:
                        try:
                            got_epoch = epoch_from_dos(info.date_time, tz)
                            if abs(got_epoch - int(want_epoch)) > 2:
                                problems.append(
                                    f"{info.filename}: 目标时间偏差过大 "
                                    f"{got_epoch} != {want_epoch}"
                                )
                        except (MoyuError, ValueError, OverflowError):
                            pass

            if no_future and epochs:
                now = int(time.time())
                future = [epoch for epoch in epochs if epoch > now + 2]
                if future:
                    problems.append(
                        f"存在未来 mtime: {format_epoch(max(future), tz)}"
                    )

            if check_crc:
                bad = zf.testzip()
                if bad:
                    problems.append(f"CRC 校验失败: {bad}")
    except (OSError, zipfile.BadZipFile) as exc:
        return {
            "ok": False,
            "problems": [f"无法读取 ZIP: {exc}"],
            "entries": entries,
            "tz": tz_name,
            "extra_ids": [],
            "compression": {},
            "archive_comment": archive_comment,
            "min_epoch": None,
            "max_epoch": None,
            "min_time": None,
            "max_time": None,
        }

    compression_names = {}
    for method, count in compression_counts.items():
        if method == zipfile.ZIP_STORED:
            name = "store"
        elif method == zipfile.ZIP_DEFLATED:
            name = "deflate"
        elif method == zipfile.ZIP_BZIP2:
            name = "bzip2"
        elif method == zipfile.ZIP_LZMA:
            name = "lzma"
        else:
            name = str(method)
        compression_names[name] = count

    min_epoch = min(epochs) if epochs else None
    max_epoch = max(epochs) if epochs else None
    return {
        "ok": not problems,
        "problems": problems,
        "entries": entries,
        "tz": tz_name,
        "extra_ids": [f"0x{header_id:04x}" for header_id in sorted(extra_ids)],
        "compression": compression_names,
        "archive_comment": archive_comment,
        "min_epoch": min_epoch,
        "max_epoch": max_epoch,
        "min_time": format_epoch(min_epoch, tz) if min_epoch is not None else None,
        "max_time": format_epoch(max_epoch, tz) if max_epoch is not None else None,
    }