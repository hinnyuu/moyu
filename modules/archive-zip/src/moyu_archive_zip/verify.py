"""ZIP structure verification.

Verification never trusts the writer. It reads central directory and local
headers, rejects unsafe names, time-bearing extra fields, comments and optional
inconsistencies, and compares the result with the expected entry list.
"""

import datetime as dt
import struct
import time
import zipfile

from .dos import encode_dos, validate_dos
from .errors import ArchiveError

TIME_EXTRA_IDS = {0x5455, 0x000A, 0x5855, 0x000D}
ZIP64_EXTRA_ID = 0x0001
UNICODE_EXTRA_IDS = {0x7075, 0x6375}


def parse_extra(extra: bytes) -> list[tuple[int, bytes]]:
    fields = []
    position = 0
    while position < len(extra):
        if position + 4 > len(extra):
            raise ArchiveError("extra 字段头被截断")
        header_id, size = struct.unpack_from("<HH", extra, position)
        position += 4
        if position + size > len(extra):
            raise ArchiveError(f"extra 0x{header_id:04x} 数据被截断")
        fields.append((header_id, extra[position : position + size]))
        position += size
    return fields


def check_extra_fields(
    fields,
    label,
    problems,
    extra_ids,
    strict,
    allow_unicode_extra,
    allow_time_extra,
):
    for header_id, data in fields:
        extra_ids.add(header_id)
        if header_id in TIME_EXTRA_IDS and not allow_time_extra:
            problems.append(f"{label}: 含时间 extra 0x{header_id:04x}")
        if header_id in UNICODE_EXTRA_IDS and not allow_unicode_extra:
            problems.append(f"{label}: 含 Unicode extra 0x{header_id:04x}")
        if header_id == ZIP64_EXTRA_ID:
            if len(data) not in (0, 8, 16, 24) or len(data) % 8:
                problems.append(f"{label}: ZIP64 extra 长度非法")
        elif strict and header_id not in TIME_EXTRA_IDS:
            problems.append(f"{label}: 含未知 extra 0x{header_id:04x}")


def read_local_header(zf, info):
    fp = zf.fp
    fp.seek(info.header_offset)
    header = fp.read(30)
    if len(header) != 30:
        raise ArchiveError("本地文件头不完整")
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
        raise ArchiveError("本地文件头签名错误")
    fp.seek(info.header_offset + 30 + name_len)
    extra = fp.read(extra_len)
    if len(extra) != extra_len:
        raise ArchiveError("本地文件头 extra 字段不完整")
    return {
        "flags": flags,
        "method": method,
        "dos_time": dos_time,
        "dos_date": dos_date,
        "extra": extra,
    }


def is_safe_arcname(name: str) -> bool:
    if not name or name.startswith(("/", "\\")) or "\\" in name:
        return False
    parts = name.split("/")
    return all(part not in ("", ".", "..") for part in parts)


def resolve_timezone(name):
    if name is None:
        return dt.timezone.utc
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception as exc:
        raise ArchiveError(f"无法解析时区: {name}") from exc


def epoch_from_dos(dos, tz):
    year, month, day, hour, minute, second = dos
    return int(dt.datetime(year, month, day, hour, minute, second, tzinfo=tz).timestamp())


def format_epoch(epoch, tz):
    return dt.datetime.fromtimestamp(epoch, tz=tz).strftime("%Y-%m-%d %H:%M:%S %Z")


def _expected_map(expected):
    if not expected:
        return None
    if isinstance(expected, dict) and "entries" in expected:
        expected = expected["entries"]
    if isinstance(expected, list):
        return {item["arcname"]: item for item in expected}
    if isinstance(expected, dict):
        return expected
    raise ArchiveError("expected 必须是条目列表或 arcname 到条目的映射")


def verify_archive(
    path,
    expected=None,
    timezone="UTC",
    strict=True,
    allow_unicode_extra=False,
    allow_time_extra=False,
    require_store=False,
    check_crc=False,
    no_future=False,
):
    problems = []
    extra_ids = set()
    compression_counts = {}
    epochs = []
    entries = 0
    archive_comment = 0
    expected_map = _expected_map(expected)
    tz = resolve_timezone(timezone)

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
                if not is_safe_arcname(label):
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
                except ArchiveError as exc:
                    problems.append(f"{label}: 中央目录 {exc}")
                else:
                    check_extra_fields(
                        central_fields,
                        f"{label} 中央目录",
                        problems,
                        extra_ids,
                        strict,
                        allow_unicode_extra,
                        allow_time_extra,
                    )

                try:
                    local = read_local_header(zf, info)
                except ArchiveError as exc:
                    problems.append(f"{label}: {exc}")
                else:
                    try:
                        local_fields = parse_extra(local["extra"])
                    except ArchiveError as exc:
                        problems.append(f"{label}: 本地文件头 {exc}")
                    else:
                        check_extra_fields(
                            local_fields,
                            f"{label} 本地文件头",
                            problems,
                            extra_ids,
                            strict,
                            allow_unicode_extra,
                            allow_time_extra,
                        )
                    try:
                        central_dos = encode_dos(info.date_time)
                    except ArchiveError as exc:
                        problems.append(f"{label}: {exc}")
                    else:
                        if (local["dos_time"], local["dos_date"]) != central_dos:
                            problems.append(f"{label}: 本地头与中央目录 DOS 时间不一致")
                    if local["method"] != info.compress_type:
                        problems.append(f"{label}: 本地头与中央目录压缩方法不一致")
                    if strict and local["flags"] & 0x1:
                        problems.append(f"{label}: 本地头标记加密")

                try:
                    validate_dos(info.date_time)
                    epoch = epoch_from_dos(info.date_time, tz)
                except (ArchiveError, ValueError, OverflowError) as exc:
                    problems.append(f"{label}: 非法 DOS 时间 {info.date_time!r}: {exc}")
                else:
                    epochs.append(epoch)

                compression_counts[info.compress_type] = (
                    compression_counts.get(info.compress_type, 0) + 1
                )
                if require_store and info.compress_type != zipfile.ZIP_STORED:
                    problems.append(f"{label}: 未使用 STORE")

            if expected_map is not None:
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
                    want_dos = want.get("dos")
                    if want_dos is not None:
                        try:
                            if tuple(want_dos) != tuple(info.date_time):
                                problems.append(
                                    f"{info.filename}: DOS 时间不匹配 "
                                    f"{info.date_time} != {tuple(want_dos)}"
                                )
                        except TypeError:
                            problems.append(f"{info.filename}: 期望中 dos 非法")
                    want_epoch = want.get("target_epoch")
                    if want_epoch is not None:
                        try:
                            got_epoch = epoch_from_dos(info.date_time, tz)
                            if abs(got_epoch - int(want_epoch)) > 2:
                                problems.append(
                                    f"{info.filename}: 目标时间偏差过大 "
                                    f"{got_epoch} != {want_epoch}"
                                )
                        except (ArchiveError, ValueError, OverflowError):
                            pass

            if no_future and epochs:
                now = int(time.time())
                future = [epoch for epoch in epochs if epoch > now + 2]
                if future:
                    problems.append(f"存在未来 mtime: {format_epoch(max(future), tz)}")

            if check_crc:
                bad = zf.testzip()
                if bad:
                    problems.append(f"CRC 校验失败: {bad}")
    except (OSError, zipfile.BadZipFile) as exc:
        return {
            "ok": False,
            "problems": [f"无法读取 ZIP: {exc}"],
            "entries": entries,
            "timezone": timezone,
            "extra_ids": [],
            "compression": {},
            "archive_comment": archive_comment,
            "min_epoch": None,
            "max_epoch": None,
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
        "timezone": timezone,
        "extra_ids": [f"0x{header_id:04x}" for header_id in sorted(extra_ids)],
        "compression": compression_names,
        "archive_comment": archive_comment,
        "min_epoch": min_epoch,
        "max_epoch": max_epoch,
    }