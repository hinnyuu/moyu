import datetime as dt
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
import zipfile
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import moyu_media

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
    result = []
    for directory in sorted(IMAGE_ROOT.iterdir()):
        if directory.is_dir():
            result.extend(sorted(path for path in directory.iterdir() if path.is_file()))
    return result


def target_strings(epoch):
    value = dt.datetime.fromtimestamp(epoch, tz=TZ)
    return {
        value.strftime("%Y/%m/%d %H:%M:%S"),
        value.strftime("%Y:%m:%d %H:%M:%S"),
        value.strftime("%Y-%m-%dT%H:%M:%S"),
    }


class MetadataRewriteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.target = int(dt.datetime(2026, 11, 5, 23, 30, 0, tzinfo=TZ).timestamp())

    def tearDown(self):
        self.tmp.cleanup()

    @unittest.skipUnless(image_files(), "图片测试集不存在")
    def test_images_rewrite_and_decode(self):
        for source in image_files():
            info = moyu_media.build_metadata_patches(str(source), self.target, TZ)
            patched_data = moyu_media.apply_patches(source.read_bytes(), info.patches)
            self.assertEqual(len(patched_data), source.stat().st_size)
            output = self.root / source.name
            output.write_bytes(patched_data)
            if info.patches:
                current = moyu_media.build_metadata_patches(
                    str(output), self.target + 3600, TZ
                )
                expected = target_strings(self.target)
                for patch in current.patches:
                    if patch.field.endswith("CRC"):
                        continue
                    self.assertIn(patch.old.decode("ascii"), expected)
            if info.format == "png":
                self.assert_png_crc(patched_data)
            if Image is not None and info.format in (
                "png",
                "jpeg",
                "tiff",
                "webp",
                "avif",
            ):
                with Image.open(output) as image:
                    image.load()

    def assert_png_crc(self, data):
        position = 8
        while position + 12 <= len(data):
            length = struct.unpack(">I", data[position : position + 4])[0]
            chunk_type = data[position + 4 : position + 8]
            body = data[position + 8 : position + 8 + length]
            actual = struct.unpack(
                ">I", data[position + 8 + length : position + 12 + length]
            )[0]
            expected = zlib.crc32(chunk_type + body) & 0xFFFFFFFF
            self.assertEqual(actual, expected, chunk_type)
            position += 12 + length
            if chunk_type == b"IEND":
                break

    @unittest.skipUnless(all(path.exists() for path in VIDEOS), "视频测试集不存在")
    def test_videos_rewrite(self):
        for source in VIDEOS:
            info = moyu_media.build_metadata_patches(str(source), self.target, TZ)
            self.assertTrue(info.patches, source.name)
            patched_data = moyu_media.apply_patches(source.read_bytes(), info.patches)
            self.assertEqual(len(patched_data), source.stat().st_size)
            output = self.root / source.name
            output.write_bytes(patched_data)
            current = moyu_media.build_metadata_patches(
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
        day = atom(
            b"\xa9day", b"\x00\x00\x00\x00" + b"2026/11/05 21:17:09"
        )
        moov = atom(
            b"moov",
            mvhd + atom(b"trak", tkhd + atom(b"mdia", mdhd)) + atom(b"udta", day),
        )
        ftyp = atom(b"ftyp", b"isom" + b"\x00\x00\x00\x00" + b"isom")
        source = self.root / "synthetic.mp4"
        source.write_bytes(ftyp + moov)
        info = moyu_media.build_metadata_patches(str(source), self.target, TZ)
        fields = {patch.field for patch in info.patches}
        self.assertIn("mvhd creation", fields)
        self.assertIn("tkhd modification", fields)
        self.assertIn("mdhd creation", fields)
        self.assertIn("mp4 ©day", fields)
        output = self.root / "synthetic-out.mp4"
        output.write_bytes(moyu_media.apply_patches(source.read_bytes(), info.patches))
        current = moyu_media.build_metadata_patches(
            str(output), self.target + 3600, TZ
        )
        new_qt = self.target + qt_epoch
        for patch in current.patches:
            if patch.field.endswith("©day"):
                self.assertEqual(patch.old, b"2026/11/05 23:30:00")
            else:
                self.assertEqual(
                    struct.unpack(">I", patch.old)[0], new_qt, patch.field
                )

    @unittest.skipUnless(
        image_files() and all(path.exists() for path in VIDEOS), "测试集不存在"
    )
    def test_pack_rewrites_metadata_and_keep_flag(self):
        source_dir = self.root / "src"
        source_dir.mkdir()
        selected = [
            IMAGE_ROOT / "PNG" / "moyu_Image0001.png",
            IMAGE_ROOT / "EXR" / "moyu_Image0001.exr",
            VIDEOS[0],
            VIDEOS[2],
        ]
        for source in selected:
            shutil.copy2(source, source_dir / source.name)
        before = {
            source.name: hashlib.sha256(source.read_bytes()).hexdigest()
            for source in selected
        }

        archive = self.root / "delivery.zip"
        manifest = self.root / "delivery.json"
        packed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "moyu-pack"),
                "-o",
                str(archive),
                "--manifest",
                str(manifest),
                "-q",
                str(source_dir),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(packed.returncode, 0, packed.stderr)
        import json

        data = json.loads(manifest.read_text(encoding="utf-8"))
        entries = {entry["arcname"]: entry for entry in data["entries"]}
        extract_dir = self.root / "out"
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(extract_dir)
        for arcname, entry in entries.items():
            extracted = extract_dir / arcname
            current = moyu_media.build_metadata_patches(
                str(extracted), entry["target_epoch"] + 3600, TZ
            )
            expected = target_strings(entry["target_epoch"])
            for patch in current.patches:
                if patch.field.endswith("CRC"):
                    continue
                self.assertIn(patch.old.decode("ascii"), expected, arcname)
        for source in selected:
            self.assertEqual(
                hashlib.sha256(source.read_bytes()).hexdigest(), before[source.name]
            )

        keep_archive = self.root / "keep.zip"
        keep_manifest = self.root / "keep.json"
        kept = subprocess.run(
            [
                sys.executable,
                str(ROOT / "moyu-pack"),
                "-o",
                str(keep_archive),
                "--manifest",
                str(keep_manifest),
                "--keep-metadata",
                "-q",
                str(source_dir / "moyu_Image0001.png"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(kept.returncode, 0, kept.stderr)
        keep_dir = self.root / "keep"
        with zipfile.ZipFile(keep_archive) as zf:
            zf.extractall(keep_dir)
        original = moyu_media.build_metadata_patches(
            str(source_dir / "moyu_Image0001.png"), self.target, TZ
        )
        kept_info = moyu_media.build_metadata_patches(
            str(keep_dir / "moyu_Image0001.png"), self.target + 3600, TZ
        )
        self.assertEqual(
            {patch.old for patch in original.patches if not patch.field.endswith("CRC")},
            {patch.old for patch in kept_info.patches if not patch.field.endswith("CRC")},
        )


if __name__ == "__main__":
    unittest.main()