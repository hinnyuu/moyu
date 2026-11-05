import datetime as dt
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import moyu_zip

TZ_NAME = "Asia/Shanghai"
TZ = moyu_zip.resolve_timezone(TZ_NAME)


def make_file(path, data, mtime_ns):
    Path(path).write_bytes(data)
    os.utime(path, ns=(mtime_ns, mtime_ns))


def run_cli(*args):
    command = [sys.executable, *[str(arg) for arg in args]]
    return subprocess.run(command, capture_output=True, text=True)


class DosTimeTests(unittest.TestCase):
    def test_odd_second_is_floored(self):
        epoch = int(dt.datetime(2026, 1, 2, 3, 4, 5, tzinfo=TZ).timestamp())
        self.assertEqual(moyu_zip.dos_datetime(epoch, TZ), (2026, 1, 2, 3, 4, 4))

    def test_encode_decode_roundtrip(self):
        for value in (
            (2026, 1, 2, 3, 4, 4),
            (1980, 1, 1, 0, 0, 0),
            (2107, 12, 31, 23, 59, 58),
        ):
            encoded = moyu_zip.encode_dos(value)
            self.assertEqual(moyu_zip.decode_dos(*encoded), value)

    def test_out_of_range(self):
        with self.assertRaises(moyu_zip.MoyuError):
            moyu_zip.encode_dos((1979, 12, 31, 23, 59, 58))


class PackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.base_ns = (
            int(dt.datetime(2025, 12, 31, 0, 0, 0, tzinfo=TZ).timestamp())
            * 1_000_000_000
        )

    def tearDown(self):
        self.tmp.cleanup()

    def make_set(self):
        paths = []
        for index, gap in enumerate((0, 10, 20)):
            path = self.root / f"frame_{index:04d}.exr"
            make_file(path, b"x" * 4096, self.base_ns + gap * 1_000_000_000)
            paths.append(str(path))
        return paths

    def test_pack_clean_and_source_untouched(self):
        paths = self.make_set()
        before = {
            path: (
                os.stat(path).st_mtime_ns,
                os.stat(path).st_ctime_ns,
                os.stat(path).st_size,
            )
            for path in paths
        }
        plans, _tz, target_ns, delta_ns = moyu_zip.plan_pack(
            paths, tz_name=TZ_NAME
        )
        output = self.root / "out.zip"
        result = moyu_zip.write_zip(
            plans,
            str(output),
            TZ_NAME,
            target_ns,
            delta_ns,
            fsync=False,
        )
        self.assertTrue(result["verified"])
        after = {
            path: (
                os.stat(path).st_mtime_ns,
                os.stat(path).st_ctime_ns,
                os.stat(path).st_size,
            )
            for path in paths
        }
        self.assertEqual(before, after)

        with zipfile.ZipFile(output) as archive:
            infos = sorted(archive.infolist(), key=lambda item: item.filename)
            self.assertEqual(len(infos), 3)
            for info in infos:
                self.assertEqual(info.extra, b"")
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
            epochs = sorted(
                moyu_zip.epoch_from_dos(info.date_time, TZ) for info in infos
            )
        self.assertEqual(epochs[1] - epochs[0], 10)
        self.assertEqual(epochs[2] - epochs[1], 10)

    def test_explicit_target(self):
        paths = self.make_set()
        plans, _tz, target_ns, delta_ns = moyu_zip.plan_pack(
            paths,
            target="2026-01-02 03:04:05",
            tz_name=TZ_NAME,
        )
        output = self.root / "target.zip"
        moyu_zip.write_zip(
            plans,
            str(output),
            TZ_NAME,
            target_ns,
            delta_ns,
            fsync=False,
        )
        with zipfile.ZipFile(output) as archive:
            latest = max(info.date_time for info in archive.infolist())
        self.assertEqual(latest, (2026, 1, 2, 3, 4, 4))

    def test_directory_layout(self):
        renders = self.root / "renders"
        beauty = renders / "beauty"
        beauty.mkdir(parents=True)
        make_file(beauty / "a.exr", b"a", self.base_ns)
        make_file(renders / "b.exr", b"b", self.base_ns + 1_000_000_000)
        plans, _tz, _target_ns, _delta_ns = moyu_zip.plan_pack(
            [str(renders)], tz_name=TZ_NAME
        )
        self.assertEqual(
            [plan.arcname for plan in plans],
            ["renders/b.exr", "renders/beauty/a.exr"],
        )

    def test_duplicate_arcname(self):
        first = self.root / "a"
        second = self.root / "b"
        first.mkdir()
        second.mkdir()
        make_file(first / "same.exr", b"1", self.base_ns)
        make_file(second / "same.exr", b"2", self.base_ns)
        with self.assertRaises(moyu_zip.MoyuError):
            moyu_zip.plan_pack(
                [str(first / "same.exr"), str(second / "same.exr")],
                tz_name=TZ_NAME,
            )

    def test_cli_pack_verify_manifest(self):
        paths = self.make_set()
        output = self.root / "cli.zip"
        manifest = self.root / "cli.json"
        packed = run_cli(
            ROOT / "moyu-pack",
            "-o",
            output,
            "--manifest",
            manifest,
            "-q",
            *paths,
        )
        self.assertEqual(packed.returncode, 0, packed.stderr)
        verified = run_cli(
            ROOT / "moyu-verify",
            "--manifest",
            manifest,
            "--require-store",
            "-q",
            output,
        )
        self.assertEqual(verified.returncode, 0, verified.stderr)

        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["entries"][0]["dos"] = [1980, 1, 1, 0, 0, 0]
        bad_manifest = self.root / "bad.json"
        bad_manifest.write_text(json.dumps(data), encoding="utf-8")
        rejected = run_cli(
            ROOT / "moyu-verify", "--manifest", bad_manifest, "-q", output
        )
        self.assertNotEqual(rejected.returncode, 0)

    def test_cli_dry_run(self):
        paths = self.make_set()
        output = self.root / "dry.zip"
        result = run_cli(ROOT / "moyu-pack", "-o", output, "--dry-run", *paths)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(output.exists())

    def test_cli_refuses_overwrite(self):
        paths = self.make_set()
        output = self.root / "exists.zip"
        output.write_bytes(b"x")
        refused = run_cli(ROOT / "moyu-pack", "-o", output, "-q", *paths)
        self.assertNotEqual(refused.returncode, 0)
        forced = run_cli(
            ROOT / "moyu-pack", "-o", output, "--force", "-q", *paths
        )
        self.assertEqual(forced.returncode, 0, forced.stderr)

    def test_special_names(self):
        names = ["带 空格.exr", "中文.png", "line\nbreak.tif"]
        paths = []
        for index, name in enumerate(names):
            path = self.root / name
            make_file(path, b"x", self.base_ns + index * 1_000_000_000)
            paths.append(str(path))
        plans, _tz, target_ns, delta_ns = moyu_zip.plan_pack(
            paths, tz_name=TZ_NAME
        )
        output = self.root / "names.zip"
        moyu_zip.write_zip(
            plans, str(output), TZ_NAME, target_ns, delta_ns, fsync=False
        )
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(
                sorted(info.filename for info in archive.infolist()),
                sorted(names),
            )
        result = moyu_zip.verify_zip(str(output), tz_name=TZ_NAME)
        self.assertTrue(result["ok"], result["problems"])

    def test_manifest_is_excluded_from_input(self):
        docs = self.root / "docs"
        docs.mkdir()
        make_file(docs / "a.exr", b"a", self.base_ns)
        output = self.root / "docs.zip"
        manifest = docs / "manifest.json"
        for _ in range(2):
            result = run_cli(
                ROOT / "moyu-pack",
                "-o",
                output,
                "--manifest",
                manifest,
                "--force",
                "-q",
                docs,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        with zipfile.ZipFile(output) as archive:
            names = {info.filename for info in archive.infolist()}
        self.assertIn("docs/a.exr", names)
        self.assertNotIn("docs/manifest.json", names)


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_rejects_ut_time_extra(self):
        bad = self.root / "ut.zip"
        with zipfile.ZipFile(bad, "w") as archive:
            info = zipfile.ZipInfo("x.exr", date_time=(2026, 1, 1, 0, 0, 0))
            info.extra = struct.pack("<HHBI", 0x5455, 5, 1, 1767225600)
            archive.writestr(info, b"data")
        result = moyu_zip.verify_zip(str(bad), tz_name=TZ_NAME)
        self.assertFalse(result["ok"])
        self.assertTrue(any("0x5455" in problem for problem in result["problems"]))

    def test_rejects_ntfs_extra(self):
        bad = self.root / "ntfs.zip"
        with zipfile.ZipFile(bad, "w") as archive:
            info = zipfile.ZipInfo("x.exr", date_time=(2026, 1, 1, 0, 0, 0))
            info.extra = struct.pack("<HH", 0x000A, 0)
            archive.writestr(info, b"data")
        result = moyu_zip.verify_zip(str(bad), tz_name=TZ_NAME)
        self.assertFalse(result["ok"])
        self.assertTrue(any("0x000a" in problem for problem in result["problems"]))

    def test_rejects_unsafe_name(self):
        bad = self.root / "unsafe.zip"
        with zipfile.ZipFile(bad, "w") as archive:
            archive.writestr("../evil.exr", b"data")
        result = moyu_zip.verify_zip(str(bad), tz_name=TZ_NAME)
        self.assertFalse(result["ok"])

    def test_accepts_clean_zip(self):
        good = self.root / "clean.zip"
        with zipfile.ZipFile(good, "w") as archive:
            info = zipfile.ZipInfo("x.exr", date_time=(2026, 1, 1, 0, 0, 0))
            archive.writestr(info, b"data")
        result = moyu_zip.verify_zip(str(good), tz_name=TZ_NAME)
        self.assertTrue(result["ok"], result["problems"])

    def test_parse_extra_truncated(self):
        with self.assertRaises(moyu_zip.MoyuError):
            moyu_zip.parse_extra(b"\x55\x54\x05")

    @unittest.skipUnless(shutil.which("zip"), "zip 不可用")
    def test_infozip_x_is_clean(self):
        source = self.root / "a.exr"
        make_file(source, b"data", 1_700_000_000 * 1_000_000_000)
        output = self.root / "x.zip"
        result = subprocess.run(
            ["zip", "-0", "-X", "-q", str(output), str(source)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        verified = moyu_zip.verify_zip(str(output), tz_name=TZ_NAME)
        self.assertTrue(verified["ok"], verified["problems"])


if __name__ == "__main__":
    unittest.main()