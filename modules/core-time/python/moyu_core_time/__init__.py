"""Python reference implementation of the core-time contract.

The Rust crate ``moyu-core`` is the normative implementation for the gateway
and WASM targets. Python services need the same semantics, so this module
mirrors it and is covered by the same behavioural cases.
"""

from dataclasses import dataclass
from typing import Sequence

__all__ = [
    "DosTime",
    "PlanEntry",
    "SourceTime",
    "TimeError",
    "TimePlan",
    "civil_from_days",
    "dos_from_unix",
    "floor_dos_second",
    "plan_times",
]


class TimeError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _error(code, message):
    return TimeError(code, message)


@dataclass(frozen=True)
class SourceTime:
    id: str
    mtime_ns: int


@dataclass(frozen=True)
class DosTime:
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int

    def __post_init__(self):
        if not 1980 <= self.year <= 2107:
            raise _error("dos_out_of_range", "DOS 时间越界")
        if not 1 <= self.month <= 12:
            raise _error("dos_out_of_range", "DOS 时间越界")
        if not 1 <= self.day <= 31:
            raise _error("dos_out_of_range", "DOS 时间越界")
        if (
            not 0 <= self.hour <= 23
            or not 0 <= self.minute <= 59
            or not 0 <= self.second <= 58
            or self.second % 2
        ):
            raise _error("dos_out_of_range", "DOS 时间越界")

    def as_tuple(self):
        return (
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            self.second,
        )

    def to_words(self):
        date = ((self.year - 1980) << 9) | (self.month << 5) | self.day
        time = (self.hour << 11) | (self.minute << 5) | (self.second // 2)
        return date, time


@dataclass(frozen=True)
class PlanEntry:
    id: str
    source_mtime_ns: int
    target_epoch: int
    dos: DosTime


@dataclass(frozen=True)
class TimePlan:
    target_epoch: int
    delta_ns: int
    utc_offset_seconds: int
    entries: tuple


def floor_dos_second(second: int) -> int:
    return second & ~1


def civil_from_days(days: int):
    z = days + 719468
    era = (z if z >= 0 else z - 146096) // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    year = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    day = doy - (153 * mp + 2) // 5 + 1
    month = mp + 3 if mp < 10 else mp - 9
    if month <= 2:
        year += 1
    return year, month, day


def dos_from_unix(epoch_seconds: int, utc_offset_seconds: int) -> DosTime:
    local = int(epoch_seconds) + int(utc_offset_seconds)
    days = local // 86_400
    seconds_of_day = local % 86_400
    year, month, day = civil_from_days(days)
    hour = seconds_of_day // 3_600
    minute = (seconds_of_day % 3_600) // 60
    second = seconds_of_day % 60
    return DosTime(year, month, day, hour, minute, floor_dos_second(second))


def plan_times(
    sources: Sequence[SourceTime],
    target_epoch: int,
    utc_offset_seconds: int,
) -> TimePlan:
    if not sources:
        raise _error("empty", "没有源文件")
    max_mtime_ns = max(source.mtime_ns for source in sources)
    delta_ns = int(target_epoch) * 1_000_000_000 - int(max_mtime_ns)
    if delta_ns <= 0:
        raise _error("target_not_later", "目标时间不晚于最新源时间")
    if delta_ns > 2**63 - 1:
        raise _error("overflow", "时间计算溢出")
    entries = []
    for source in sources:
        target = (int(source.mtime_ns) + delta_ns) // 1_000_000_000
        dos = dos_from_unix(target, utc_offset_seconds)
        entries.append(
            PlanEntry(
                id=source.id,
                source_mtime_ns=source.mtime_ns,
                target_epoch=target,
                dos=dos,
            )
        )
    return TimePlan(
        target_epoch=int(target_epoch),
        delta_ns=delta_ns,
        utc_offset_seconds=int(utc_offset_seconds),
        entries=tuple(entries),
    )