"""DOS timestamp helpers used by ZIP entries.

ZIP stores modification time as two 16-bit words with a two-second resolution.
A DOS timestamp is a tuple ``(year, month, day, hour, minute, second)``.
"""

from .errors import ArchiveError

DOS_YEAR_MIN = 1980
DOS_YEAR_MAX = 2107


def validate_dos(value) -> tuple:
    try:
        year, month, day, hour, minute, second = value
    except (TypeError, ValueError) as exc:
        raise ArchiveError(f"DOS 时间必须是 6 元组: {value!r}") from exc
    if not all(isinstance(part, int) for part in value):
        raise ArchiveError(f"DOS 时间必须是整数: {value!r}")
    if not DOS_YEAR_MIN <= year <= DOS_YEAR_MAX:
        raise ArchiveError(f"DOS 年份超出 {DOS_YEAR_MIN}-{DOS_YEAR_MAX}: {value!r}")
    if not 1 <= month <= 12:
        raise ArchiveError(f"DOS 月份非法: {value!r}")
    if not 1 <= day <= 31:
        raise ArchiveError(f"DOS 日期非法: {value!r}")
    if not 0 <= hour <= 23:
        raise ArchiveError(f"DOS 小时非法: {value!r}")
    if not 0 <= minute <= 59:
        raise ArchiveError(f"DOS 分钟非法: {value!r}")
    if not 0 <= second <= 58 or second % 2:
        raise ArchiveError(f"DOS 秒必须是 0-58 的偶数: {value!r}")
    return tuple(value)


def encode_dos(value) -> tuple[int, int]:
    year, month, day, hour, minute, second = validate_dos(value)
    dos_time = (hour << 11) | (minute << 5) | (second // 2)
    dos_date = ((year - DOS_YEAR_MIN) << 9) | (month << 5) | day
    return dos_time, dos_date


def decode_dos(dos_time: int, dos_date: int) -> tuple:
    return (
        ((dos_date >> 9) & 0x7F) + DOS_YEAR_MIN,
        (dos_date >> 5) & 0x0F,
        dos_date & 0x1F,
        (dos_time >> 11) & 0x1F,
        (dos_time >> 5) & 0x3F,
        (dos_time & 0x1F) * 2,
    )