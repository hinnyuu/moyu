"""Streaming ZIP writer with atomic replacement.

The writer accepts caller-provided DOS timestamps and byte streams. It writes
to a ``.part`` file in the destination directory, optionally verifies the
result, then atomically replaces the target. Source files are never modified.
"""

import os
import tempfile
import time
import zipfile
from dataclasses import dataclass

from .dos import validate_dos
from .errors import ArchiveError
from .verify import is_safe_arcname, verify_archive

DEFAULT_CHUNK_SIZE = 1024 * 1024
COMPRESSION_STORE = "store"
COMPRESSION_DEFLATE = "deflate"


@dataclass
class ArchiveSummary:
    output: str
    entries: int
    total_bytes: int
    archive_bytes: int
    compression: str
    elapsed_sec: float
    verified: bool
    extra_ids: list

    def to_dict(self):
        return {
            "output": self.output,
            "entries": self.entries,
            "total_bytes": self.total_bytes,
            "archive_bytes": self.archive_bytes,
            "compression": self.compression,
            "elapsed_sec": self.elapsed_sec,
            "verified": self.verified,
            "extra_ids": list(self.extra_ids),
        }


def _iter_chunks(stream, chunk_size):
    read = getattr(stream, "read", None)
    if read is not None:
        while True:
            chunk = read(chunk_size)
            if not chunk:
                break
            yield chunk
        return
    for chunk in stream:
        if chunk:
            yield chunk


class ArchiveWriter:
    def __init__(
        self,
        output,
        compression=COMPRESSION_STORE,
        force=False,
        fsync=True,
        verify=True,
        timezone="UTC",
        chunk_size=DEFAULT_CHUNK_SIZE,
    ):
        if compression not in (COMPRESSION_STORE, COMPRESSION_DEFLATE):
            raise ArchiveError(f"不支持的压缩方式: {compression}")
        if chunk_size <= 0:
            raise ArchiveError("chunk_size 必须大于 0")
        self.output = os.path.abspath(output)
        self.compression = compression
        self.fsync = fsync
        self.verify = verify
        self.timezone = timezone
        self.chunk_size = chunk_size
        self._method = (
            zipfile.ZIP_DEFLATED
            if compression == COMPRESSION_DEFLATE
            else zipfile.ZIP_STORED
        )
        self._entries = {}
        self._total_bytes = 0
        self._started = None
        self._tmp_path = None
        self._fp = None
        self._zf = None
        self._closed = False

        outdir = os.path.dirname(self.output) or "."
        os.makedirs(outdir, exist_ok=True)
        if os.path.isdir(self.output):
            raise ArchiveError(f"输出路径是目录: {output}")
        if os.path.exists(self.output) and not force:
            raise ArchiveError(f"输出已存在，需要显式覆盖: {output}")

        fd, self._tmp_path = tempfile.mkstemp(
            prefix=".moyu-zip-", suffix=".part", dir=outdir
        )
        os.close(fd)
        try:
            os.chmod(self._tmp_path, 0o644)
        except OSError:
            pass
        self._started = time.monotonic()
        self._fp = open(self._tmp_path, "wb", buffering=4 * 1024 * 1024)
        self._zf = zipfile.ZipFile(
            self._fp,
            "w",
            compression=self._method,
            allowZip64=True,
            compresslevel=1 if self._method == zipfile.ZIP_DEFLATED else None,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            self.abort()
            return False
        self.finalize()
        return False

    def add_entry(self, arcname, dos_time, stream, size=None, mode=0o644, force_zip64=False):
        self._ensure_open()
        if not isinstance(arcname, str) or not is_safe_arcname(arcname):
            raise ArchiveError(f"不安全的归档路径: {arcname!r}")
        if arcname in self._entries:
            raise ArchiveError(f"重复的归档路径: {arcname}")
        dos = validate_dos(dos_time)

        zinfo = zipfile.ZipInfo(arcname, date_time=dos)
        zinfo.compress_type = self._method
        zinfo.create_system = 3
        zinfo.external_attr = (mode & 0xFFFF) << 16
        zinfo.extra = b""
        zinfo.comment = b""
        if self._method == zipfile.ZIP_DEFLATED:
            zinfo._compresslevel = 1

        force_zip64 = force_zip64 or (size is not None and size > zipfile.ZIP64_LIMIT)
        written = 0
        with self._zf.open(zinfo, "w", force_zip64=force_zip64) as dst:
            for chunk in _iter_chunks(stream, self.chunk_size):
                dst.write(chunk)
                written += len(chunk)

        if size is not None and written != size:
            raise ArchiveError(
                f"{arcname}: 期望 {size} 字节，实际写入 {written} 字节"
            )
        self._entries[arcname] = {"dos": list(dos)}
        self._total_bytes += written
        return written

    def add_file(self, arcname, dos_time, path, mode=0o644):
        stat_before = os.stat(path)
        with open(path, "rb") as stream:
            written = self.add_entry(
                arcname,
                dos_time,
                stream,
                size=stat_before.st_size,
                mode=mode,
            )
        stat_after = os.stat(path)
        if (
            stat_after.st_size != stat_before.st_size
            or stat_after.st_mtime_ns != stat_before.st_mtime_ns
        ):
            raise ArchiveError(f"写入过程中源文件发生变化: {path}")
        return written

    def finalize(self):
        self._ensure_open()
        self._closed = True
        try:
            self._zf.close()
            self._fp.flush()
            if self.fsync:
                os.fsync(self._fp.fileno())
            self._fp.close()
            self._zf = None
            self._fp = None

            expected = dict(self._entries)
            result = {"ok": False, "problems": ["跳过校验"], "extra_ids": []}
            if self.verify:
                result = verify_archive(
                    self._tmp_path,
                    expected=expected,
                    timezone=self.timezone,
                    strict=True,
                    require_store=self._method == zipfile.ZIP_STORED,
                    check_crc=True,
                )
                if not result["ok"]:
                    raise ArchiveError(
                        "写入后校验失败: " + "; ".join(result["problems"][:5])
                    )

            os.replace(self._tmp_path, self.output)
            self._tmp_path = None
            elapsed = time.monotonic() - self._started
            return ArchiveSummary(
                output=self.output,
                entries=len(self._entries),
                total_bytes=self._total_bytes,
                archive_bytes=os.path.getsize(self.output),
                compression=self.compression,
                elapsed_sec=elapsed,
                verified=bool(self.verify and result["ok"]),
                extra_ids=result["extra_ids"],
            )
        except Exception:
            self._cleanup_tmp()
            raise

    def abort(self):
        self._closed = True
        if self._zf is not None:
            try:
                self._zf.close()
            except Exception:
                pass
        if self._fp is not None:
            try:
                self._fp.close()
            except Exception:
                pass
        self._zf = None
        self._fp = None
        self._cleanup_tmp()

    def _cleanup_tmp(self):
        if self._tmp_path and os.path.exists(self._tmp_path):
            try:
                os.unlink(self._tmp_path)
            except OSError:
                pass
        self._tmp_path = None

    def _ensure_open(self):
        if self._closed:
            raise ArchiveError("归档写入器已关闭")