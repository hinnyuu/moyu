import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "modules" / "core-time" / "python"))

from moyu_core_time import (  # noqa: E402
    DosTime,
    SourceTime,
    TimeError,
    civil_from_days,
    dos_from_unix,
    floor_dos_second,
    plan_times,
)


class DosTimeTests(unittest.TestCase):
    def test_to_words(self):
        dos = DosTime(1980, 1, 2, 12, 34, 56)
        date, time = dos.to_words()
        self.assertEqual(date, 34)
        self.assertEqual(time, (12 << 11) | (34 << 5) | 28)

    def test_floor_second(self):
        self.assertEqual(floor_dos_second(0), 0)
        self.assertEqual(floor_dos_second(1), 0)
        self.assertEqual(floor_dos_second(57), 56)
        self.assertEqual(floor_dos_second(58), 58)

    def test_rejects_out_of_range(self):
        for args in (
            (1979, 1, 1, 0, 0, 0),
            (2026, 13, 1, 0, 0, 0),
            (2026, 1, 32, 0, 0, 0),
            (2026, 1, 1, 24, 0, 0),
            (2026, 1, 1, 0, 60, 0),
            (2026, 1, 1, 0, 0, 59),
            (2026, 1, 1, 0, 0, 3),
        ):
            with self.assertRaises(TimeError) as ctx:
                DosTime(*args)
            self.assertEqual(ctx.exception.code, "dos_out_of_range")


class CivilTests(unittest.TestCase):
    def test_known_days(self):
        self.assertEqual(civil_from_days(0), (1970, 1, 1))
        self.assertEqual(civil_from_days(365), (1971, 1, 1))
        self.assertEqual(civil_from_days(10_957), (2000, 1, 1))

    def test_epoch_to_dos(self):
        dos = dos_from_unix(315_532_800, 0)
        self.assertEqual(dos.as_tuple(), (1980, 1, 1, 0, 0, 0))
        dos = dos_from_unix(315_532_800 + 86_400 + 45_296, 0)
        self.assertEqual(dos.as_tuple(), (1980, 1, 2, 12, 34, 56))
        date, time = dos.to_words()
        self.assertEqual(date, 34)
        self.assertEqual(time, (12 << 11) | (34 << 5) | 28)

    def test_offset_applied(self):
        dos = dos_from_unix(315_532_800, 8 * 3_600)
        self.assertEqual(dos.as_tuple(), (1980, 1, 1, 8, 0, 0))


class PlanTests(unittest.TestCase):
    def test_plans_relative_times(self):
        target = 1_800_000_000
        sources = [
            SourceTime("a", (target - 100) * 1_000_000_000),
            SourceTime("b", (target - 90) * 1_000_000_000),
            SourceTime("c", (target - 80) * 1_000_000_000),
        ]
        plan = plan_times(sources, target, 8 * 3_600)
        self.assertEqual(plan.delta_ns, 80_000_000_000)
        self.assertEqual([e.target_epoch for e in plan.entries], [target - 20, target - 10, target])
        self.assertEqual(plan.entries[0].dos.year, 2027)

    def test_rejects_empty_and_late_target(self):
        with self.assertRaises(TimeError) as ctx:
            plan_times([], 0, 0)
        self.assertEqual(ctx.exception.code, "empty")
        source = SourceTime("a", 1_800_000_000_000_000_000)
        with self.assertRaises(TimeError) as ctx:
            plan_times([source], 1_800_000_000, 0)
        self.assertEqual(ctx.exception.code, "target_not_later")


if __name__ == "__main__":
    unittest.main()