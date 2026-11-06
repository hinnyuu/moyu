import datetime as dt
import hashlib
import json
import os
import struct
import sys
import tempfile
import unittest
import zlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for relative in (
    "modules/pipeline/src",
    "modules/core-time/python",
    "modules/media-metadata/src",
    "modules/archive-zip/src",
):
    sys.path.insert(0, str(ROOT / relative))

from moyu_pipeline import PackError, PackInput, pack  # noqa: E402

try:
    from PIL import Image
except ImportError:
    Image = None

TARGET = int(dt.datetime(2026, 11, 5, 23, 30, 0, tzinfo=dt.timezone.utc).timestamp())


def make_file(path, data, mtime_ns):
    Path(path).write_bytes(data)
    os.utime(path, ns=(mtime_ns, mtime_ns))


def png_chunk(prefix, payload, suffix=b""):
    body = prefix + payload + suffix
    length = struct.pack(">I", len(body))
    crc = struct.pack(">I", zlib.crc32(prefix + body) & 0xFFFFFFFF)
    return length + prefix + body + crc


def png_with_text(path, compressed=False):
    base = path.with_suffix(".base.png")
    Image.new("RGB", (16, 16), (1, 2, 3)).save(base)
    data = base.read_bytes()
    ihdr_length = struct.unpack(">I", data[8:12])[0]
    insert_at = 8 + 12 + ihdr_length
    if compressed:
        chunk = png_chunk(
            b"zTXt", b"Date\x00\x00" + zlib.compress(b"2026/11/05 21:17:09", 6)
        )
    else:
        chunk = png_chunk(b"tEXt", b"Date\x00" + b"2026/11/05 21:17:09")
    path.write_bytes(data[:insert_at] + chunk + data[insert_at:])
    base.unlink()


def target_strings():
    value = dt.datetime.fromtimestamp(TARGET, tz=dt.timezone.utc)
    return {
        value.strftime("%Y/%m/%d %H:%M:%S"),
        value.strftime("%Y:%m:%d %H:%M:%S"),
        value.strftime("%Y-%m-%dT%H:%M:%S"),
    }


class PackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_plain_files_and_manifest(self):
        inputs = []
        mtimes = []
        for index, gap in enumerate((0, 10, 20)):
            source = self.root / f"frame_{index}.bin"
            mtime_ns = (TARGET - 100 + gap) * 1_000_000_000
            make_file(source, b"x" * 64, mtime_ns)
            mtimes.append(mtime_ns)
            inputs.append(PackInput(str(source), f"frames/frame_{index}.bin"))

        output = self.root / "out.zip"
        manifest_path = self.root / "manifest.json"
        result = pack(inputs, TARGET, output, manifest_path=manifest_path)

        self.assertTrue(result["verify"]["ok"], result["verify"]["problems"])
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["target_epoch"], TARGET)
        self.assertEqual(len(manifest["entries"]), 3)
        self.assertEqual(manifest["entries"][0]["target_epoch"], TARGET - 20)
        self.assertEqual(manifest["entries"][2]["target_epoch"], TARGET)
        self.assertEqual(manifest["archive_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())

        with zipfile.ZipFile(output) as zf:
            names = zf.namelist()
            self.assertEqual(names, [f"frames/frame_{i}.bin" for i in range(3)])
            for info in zf.infolist():
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(info.extra, b"")
        for source, mtime_ns in zip([item.source for item in inputs], mtimes):
            self.assertEqual(os.stat(source).st_mtime_ns, mtime_ns)

    @unittest.skipUnless(Image is not None, "Pillow 不可用")
    def test_png_metadata_is_rewritten_in_archive(self):
        source = self.root / "frame.png"
        png_with_text(source)
        old_ns = (TARGET - 100) * 1_000_000_000
        os.utime(source, ns=(old_ns, old_ns))
        original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        output = self.root / "out.zip"
        manifest_path = self.root / "manifest.json"
        result = pack(
            [PackInput(str(source), "frame.png")],
            TARGET,
            output,
            manifest_path=manifest_path,
        )
        self.assertTrue(result["verify"]["ok"], result["verify"]["problems"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry = manifest["entries"][0]
        self.assertEqual(entry["metadata"]["format"], "png")
        self.assertTrue(entry["metadata"]["fields"])
        with zipfile.ZipFile(output) as zf:
            data = zf.read("frame.png")
        self.assertEqual(len(data), source.stat().st_size)
        self.assertIn(b"2026/11/05 23:30:00", data)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original_hash)

    @unittest.skipUnless(Image is not None, "Pillow 不可用")
    def test_compressed_png_is_materialized(self):
        source = self.root / "frame.png"
        png_with_text(source, compressed=True)
        old_ns = (TARGET - 90) * 1_000_000_000
        os.utime(source, ns=(old_ns, old_ns))
        original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        output = self.root / "out.zip"
        result = pack(
            [PackInput(str(source), "frame.png")], TARGET, output
        )
        self.assertTrue(result["verify"]["ok"], result["verify"]["problems"])
        self.assertEqual(result["manifest"]["entries"][0]["metadata"]["mode"], "materialize")
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original_hash)
        self.assertEqual(list(self.root.glob(".moyu-meta-*")), [])
        with zipfile.ZipFile(output) as zf:
            data = zf.read("frame.png")
        extracted = self.root / "extracted.png"
        extracted.write_bytes(data)
        with Image.open(extracted) as image:
            image.load()

    def test_strict_metadata_rejects_unknown_format(self):
        source = self.root / "note.txt"
        make_file(source, b"hello", TARGET * 1_000_000_000 - 10_000_000_000)
        with self.assertRaises(PackError) as ctx:
            pack(
                [PackInput(str(source), "note.txt")],
                TARGET,
                self.root / "out.zip",
                strict_metadata=True,
            )
        self.assertEqual(ctx.exception.code, "metadata_strict")
        self.assertFalse((self.root / "out.zip").exists())

    def test_target_not_later(self):
        source = self.root / "a.bin"
        make_file(source, b"x", TARGET * 1_000_000_000)
        with self.assertRaises(PackError) as ctx:
            pack([PackInput(str(source), "a.bin")], TARGET, self.root / "out.zip")
        self.assertEqual(ctx.exception.code, "target_not_later")
        self.assertFalse((self.root / "out.zip").exists())

    def test_duplicate_arcname_and_missing_source(self):
        source = self.root / "a.bin"
        make_file(source, b"x", TARGET * 1_000_000_000 - 1_000_000_000)
        with self.assertRaises(PackError) as ctx:
            pack(
                [PackInput(str(source), "a.bin"), PackInput(str(source), "a.bin")],
                TARGET,
                self.root / "out.zip",
            )
        self.assertEqual(ctx.exception.code, "duplicate_arcname")
        with self.assertRaises(PackError) as ctx:
            pack(
                [PackInput(str(self.root / "missing.bin"), "missing.bin")],
                TARGET,
                self.root / "out.zip",
            )
        self.assertEqual(ctx.exception.code, "source_missing")

    def test_timezone_offset(self):
        source = self.root / "a.bin"
        make_file(source, b"x", TARGET * 1_000_000_000 - 1_000_000_000)
        output = self.root / "out.zip"
        result = pack(
            [PackInput(str(source), "a.bin")],
            TARGET,
            output,
            timezone="Asia/Shanghai",
        )
        self.assertTrue(result["verify"]["ok"], result["verify"]["problems"])
        with zipfile.ZipFile(output) as zf:
            info = zf.infolist()[0]
        self.assertEqual(info.date_time[3], 7)
        self.assertEqual(info.date_time[4], 30)


if __name__ == "__main__":
    unittest.main()