import os
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from moyu_archive_zip import (  # noqa: E402
    ArchiveError,
    ArchiveWriter,
    decode_dos,
    encode_dos,
    validate_dos,
    verify_archive,
)

DOS = (2026, 1, 2, 3, 4, 4)


class DosTests(unittest.TestCase):
    def test_roundtrip(self):
        for value in ((1980, 1, 1, 0, 0, 0), (2107, 12, 31, 23, 59, 58), DOS):
            encoded = encode_dos(value)
            self.assertEqual(decode_dos(*encoded), value)

    def test_rejects_invalid(self):
        for value in (
            (1979, 12, 31, 23, 59, 58),
            (2108, 1, 1, 0, 0, 0),
            (2026, 13, 1, 0, 0, 0),
            (2026, 1, 32, 0, 0, 0),
            (2026, 1, 1, 24, 0, 0),
            (2026, 1, 1, 0, 60, 0),
            (2026, 1, 1, 0, 0, 59),
            (2026, 1, 1, 0, 0, 3),
        ):
            with self.assertRaises(ArchiveError):
                validate_dos(value)


class WriterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_writes_clean_store_archive(self):
        output = self.root / "out.zip"
        writer = ArchiveWriter(output)
        writer.add_entry("dir/a.txt", DOS, [b"hello ", b"world"])
        summary = writer.finalize()

        self.assertTrue(summary.verified)
        self.assertEqual(summary.entries, 1)
        self.assertEqual(summary.total_bytes, 11)
        self.assertEqual(summary.compression, "store")
        self.assertTrue(output.exists())
        result = verify_archive(output, {"dir/a.txt": {"dos": DOS}})
        self.assertTrue(result["ok"], result["problems"])
        self.assertEqual(result["compression"], {"store": 1})

    def test_existing_output_requires_force(self):
        output = self.root / "out.zip"
        output.write_bytes(b"old")
        with self.assertRaises(ArchiveError):
            ArchiveWriter(output)
        with ArchiveWriter(output, force=True) as writer:
            writer.add_entry("a.txt", DOS, [b"x"])

    def test_unsafe_and_duplicate_names(self):
        output = self.root / "out.zip"
        with ArchiveWriter(output) as writer:
            for name in ("/abs.txt", "../up.txt", "a/../b.txt", "a\\b.txt", ""):
                with self.assertRaises(ArchiveError):
                    writer.add_entry(name, DOS, [b"x"])
            writer.add_entry("ok.txt", DOS, [b"x"])
            with self.assertRaises(ArchiveError):
                writer.add_entry("ok.txt", DOS, [b"y"])

    def test_size_mismatch_fails_and_leaves_no_output(self):
        output = self.root / "out.zip"
        writer = ArchiveWriter(output)
        with self.assertRaises(ArchiveError):
            writer.add_entry("a.txt", DOS, [b"abc"], size=10)
        writer.abort()
        self.assertFalse(output.exists())

    def test_add_file_writes_source_bytes(self):
        source = self.root / "src.bin"
        source.write_bytes(b"payload")
        output = self.root / "out.zip"
        writer = ArchiveWriter(output)
        written = writer.add_file("src.bin", DOS, source)
        summary = writer.finalize()
        self.assertEqual(written, 7)
        self.assertEqual(summary.total_bytes, 7)
        result = verify_archive(output, {"src.bin": {"dos": DOS}})
        self.assertTrue(result["ok"], result["problems"])

    def test_deflate_mode(self):
        output = self.root / "out.zip"
        with ArchiveWriter(output, compression="deflate") as writer:
            writer.add_entry("a.txt", DOS, [b"a" * 4096])
        result = verify_archive(output, require_store=False)
        self.assertTrue(result["ok"], result["problems"])
        self.assertEqual(result["compression"], {"deflate": 1})

    def test_forced_zip64_extra_is_allowed(self):
        output = self.root / "out.zip"
        with ArchiveWriter(output) as writer:
            writer.add_entry("a.txt", DOS, [b"x"], force_zip64=True)

    def test_zip64_entry_count(self):
        output = self.root / "many.zip"
        total = 65_536
        writer = ArchiveWriter(output, verify=False)
        for index in range(total):
            writer.add_entry(f"f/{index}.txt", DOS, [b"x"])
        writer.finalize()
        result = verify_archive(output, check_crc=False)
        self.assertTrue(result["ok"], result["problems"][:3])
        self.assertEqual(result["entries"], total)
        with zipfile.ZipFile(output) as zf:
            self.assertEqual(len(zf.infolist()), total)

    def test_part_file_is_removed_on_abort(self):
        output = self.root / "out.zip"
        writer = ArchiveWriter(output)
        writer.add_entry("a.txt", DOS, [b"x"])
        writer.abort()
        self.assertFalse(output.exists())
        self.assertEqual(list(self.root.glob(".moyu-zip-*.part")), [])


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_zip(self, extra=b"", name="a.txt", dos=(2026, 1, 2, 3, 4, 4)):
        path = self.root / "raw.zip"
        info = zipfile.ZipInfo(name, date_time=dos)
        info.extra = extra
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr(info, b"data")
        return path

    def test_rejects_ut_time_extra(self):
        extra = struct.pack("<HHBI", 0x5455, 5, 1, 0)
        path = self._write_zip(extra=extra)
        result = verify_archive(path)
        self.assertFalse(result["ok"])
        self.assertTrue(any("时间 extra" in problem for problem in result["problems"]))
        result = verify_archive(path, allow_time_extra=True)
        self.assertTrue(result["ok"], result["problems"])

    def test_rejects_unsafe_name(self):
        path = self._write_zip(name="../evil.txt")
        result = verify_archive(path)
        self.assertFalse(result["ok"])

    def test_rejects_unknown_extra_when_strict(self):
        extra = struct.pack("<HH", 0x9901, 0)
        path = self._write_zip(extra=extra)
        result = verify_archive(path, strict=True)
        self.assertFalse(result["ok"])
        result = verify_archive(path, strict=False)
        self.assertTrue(result["ok"], result["problems"])

    def test_expected_entries_mismatch(self):
        path = self._write_zip()
        result = verify_archive(path, {"a.txt": {"dos": (2026, 1, 2, 3, 4, 6)}})
        self.assertFalse(result["ok"])
        self.assertTrue(any("DOS 时间不匹配" in problem for problem in result["problems"]))

    def test_crc_check(self):
        path = self._write_zip()
        data = bytearray(path.read_bytes())
        with zipfile.ZipFile(path) as zf:
            offset = zf.getinfo("a.txt").header_offset + 30 + len("a.txt")
        data[offset] ^= 0xFF
        path.write_bytes(data)
        result = verify_archive(path, check_crc=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("CRC" in problem for problem in result["problems"]))


if __name__ == "__main__":
    unittest.main()