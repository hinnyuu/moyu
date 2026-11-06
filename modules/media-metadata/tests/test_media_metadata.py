import datetime as dt
import hashlib
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "modules" / "media-metadata" / "src"))

import moyu_media_metadata as md  # noqa: E402

try:
    from PIL import Image
except ImportError:
    Image = None

TZ = ZoneInfo("Asia/Shanghai")
IMAGE_ROOT = Path("/tmp/moyu-selftest")
VIDEOS = [
    Path("/root/.local/share/codeartsdoer/attachments/efcc4b5b11b5e736/moyu0001-0003.mp4"),
    Path("/root/.local/share/codeartsdoer/attachments/b8c1bc3d3444121d/moyu0001-0003.mov"),
    Path("/root/.local/share/codeartsdoer/attachments/6a767bd5c6fbae00/moyu0001-0003.mkv"),
]


def image_files():
    if not IMAGE_ROOT.exists():
        return []
    files = []
    for directory in sorted(IMAGE_ROOT.iterdir()):
        if directory.is_dir():
            files.extend(sorted(p for p in directory.iterdir() if p.is_file()))
    return files


def target_strings(epoch):
    value = dt.datetime.fromtimestamp(epoch, tz=TZ)
    return {
        value.strftime("%Y/%m/%d %H:%M:%S"),
        value.strftime("%Y:%m:%d %H:%M:%S"),
        value.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def png_crc_ok(data):
    position = 8
    while position + 12 <= len(data):
        length = struct.unpack(">I", data[position : position + 4])[0]
        chunk_type = data[position + 4 : position + 8]
        body = data[position + 8 : position + 8 + length]
        actual = struct.unpack(
            ">I", data[position + 8 + length : position + 12 + length]
        )[0]
        if actual != zlib.crc32(chunk_type + body) & 0xFFFFFFFF:
            return False
        position += 12 + length
        if chunk_type == b"IEND":
            break
    return True


class MediaMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.target = int(dt.datetime(2026, 11, 5, 23, 30, 0, tzinfo=TZ).timestamp())

    def tearDown(self):
        self.tmp.cleanup()

    @unittest.skipUnless(image_files(), "图片测试集不存在")
    def test_images_rewrite_and_decode(self):
        for source in image_files():
            info = md.build_metadata_patches(str(source), self.target, TZ)
            patched = md.apply_patches(source.read_bytes(), info.patches)
            self.assertEqual(len(patched), source.stat().st_size)
            output = self.root / source.name
            output.write_bytes(patched)
            if info.patches:
                current = md.build_metadata_patches(
                    str(output), self.target + 3600, TZ
                )
                expected = target_strings(self.target)
                for patch in current.patches:
                    if patch.field.endswith("CRC"):
                        continue
                    self.assertIn(patch.old.decode("ascii"), expected, patch.field)
            if info.format == "png":
                self.assertTrue(png_crc_ok(patched))
            if Image is not None and info.format in (
                "png",
                "jpeg",
                "tiff",
                "webp",
                "avif",
            ):
                with Image.open(output) as image:
                    image.load()

    @unittest.skipUnless(all(path.exists() for path in VIDEOS), "视频测试集不存在")
    def test_videos_rewrite(self):
        for source in VIDEOS:
            info = md.build_metadata_patches(str(source), self.target, TZ)
            self.assertTrue(info.patches, source.name)
            patched = md.apply_patches(source.read_bytes(), info.patches)
            self.assertEqual(len(patched), source.stat().st_size)
            output = self.root / source.name
            output.write_bytes(patched)
            current = md.build_metadata_patches(
                str(output), self.target + 3600, TZ
            )
            expected = target_strings(self.target)
            for patch in current.patches:
                self.assertIn(patch.old.decode("ascii"), expected, patch.field)

    def test_mp4_container_times_synthetic(self):
        def atom(atom_type, body):
            return struct.pack(">I", 8 + len(body)) + atom_type + body

        qt_epoch = 2082844800
        old_qt = int(dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc).timestamp()) + qt_epoch
        mvhd = atom(
            b"mvhd",
            b"\x00\x00\x00\x00" + struct.pack(">II", old_qt, old_qt) + b"\x00" * 92,
        )
        tkhd = atom(
            b"tkhd",
            b"\x00\x00\x00\x00" + struct.pack(">II", old_qt, old_qt) + b"\x00" * 84,
        )
        mdhd = atom(
            b"mdhd",
            b"\x00\x00\x00\x00" + struct.pack(">II", old_qt, old_qt) + b"\x00" * 24,
        )
        day = atom(b"\xa9day", b"\x00\x00\x00\x00" + b"2026/11/05 21:17:09")
        moov = atom(
            b"moov",
            mvhd + atom(b"trak", tkhd + atom(b"mdia", mdhd)) + atom(b"udta", day),
        )
        ftyp = atom(b"ftyp", b"isom" + b"\x00\x00\x00\x00" + b"isom")
        source = self.root / "synthetic.mp4"
        source.write_bytes(ftyp + moov)

        info = md.build_metadata_patches(str(source), self.target, TZ)
        fields = {patch.field for patch in info.patches}
        self.assertIn("mvhd creation", fields)
        self.assertIn("tkhd modification", fields)
        self.assertIn("mdhd creation", fields)
        self.assertIn("mp4 ©day", fields)

        output = self.root / "synthetic-out.mp4"
        output.write_bytes(md.apply_patches(source.read_bytes(), info.patches))
        current = md.build_metadata_patches(str(output), self.target + 3600, TZ)
        new_qt = self.target + qt_epoch
        for patch in current.patches:
            if patch.field.endswith("©day"):
                self.assertEqual(patch.old, b"2026/11/05 23:30:00")
            else:
                self.assertEqual(struct.unpack(">I", patch.old)[0], new_qt, patch.field)

    @unittest.skipUnless(Image is not None, "Pillow 不可用")
    def test_png_compressed_ztxt_materialize(self):
        base = self.root / "base.png"
        Image.new("RGB", (16, 16), (1, 2, 3)).save(base)
        data = base.read_bytes()
        ihdr_length = struct.unpack(">I", data[8:12])[0]
        insert_at = 8 + 12 + ihdr_length
        payload = b"Date\x00\x00" + zlib.compress(b"2026/11/05 21:17:09", 6)
        chunk = (
            struct.pack(">I", len(payload))
            + b"zTXt"
            + payload
            + struct.pack(">I", zlib.crc32(b"zTXt" + payload) & 0xFFFFFFFF)
        )
        source = self.root / "ztxt.png"
        source.write_bytes(data[:insert_at] + chunk + data[insert_at:])
        original_hash = hashlib.sha256(source.read_bytes()).hexdigest()

        info = md.build_metadata_patches(str(source), self.target, TZ)
        self.assertTrue(info.requires_materialize)
        self.assertTrue(info.records)
        self.assertFalse(info.strict_problems)

        materialized = md.materialize_metadata(
            str(source), info, self.target, TZ, str(self.root)
        )
        self.assertIsNotNone(materialized)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original_hash)
        self.assertEqual(png_crc_ok(Path(materialized).read_bytes()), True)

        current = md.build_metadata_patches(materialized, self.target + 3600, TZ)
        self.assertTrue(current.records)
        self.assertIn(current.records[0]["old"], target_strings(self.target))
        with Image.open(materialized) as image:
            image.load()
        Path(materialized).unlink()

    def test_unknown_format_reports_strict_problem(self):
        source = self.root / "note.txt"
        source.write_text("hello", encoding="utf-8")
        self.assertIsNone(md.detect_format(str(source)))
        info = md.build_metadata_patches(str(source), self.target, TZ)
        self.assertEqual(info.format, "unknown")
        self.assertTrue(info.strict_problems)


class AdapterTests(unittest.TestCase):
    def test_header_detection(self):
        cases = {
            "exr": b"v/1\x01",
            "png": b"\x89PNG\r\n\x1a\n",
            "jpeg": b"\xff\xd8\xff\xe0",
            "tiff": b"II*\x00",
            "webp": b"RIFF\x00\x00\x00\x00WEBP",
            "mkv": b"\x1a\x45\xdf\xa3",
            "mp4": b"\x00\x00\x00\x18ftypisom",
        }
        for name, header in cases.items():
            adapter = md.adapter_by_name(name)
            self.assertIsNotNone(adapter, name)
            self.assertTrue(adapter.detect(header), name)

    def test_unknown_format(self):
        self.assertIsNone(md.adapter_by_name("nope"))
        self.assertFalse(md.ADAPTERS["png"].detect(b"not a png"))

    @unittest.skipUnless(image_files(), "图片测试集不存在")
    def test_adapter_for_asset(self):
        source = sorted(image_files())[0]
        adapter = md.adapter_for(str(source))
        self.assertIsNotNone(adapter, source)
        target = int(dt.datetime(2026, 11, 5, 23, 30, 0, tzinfo=TZ).timestamp())
        info = adapter.inspect(str(source), target, TZ)
        self.assertEqual(info.format, adapter.format)


if __name__ == "__main__":
    unittest.main()