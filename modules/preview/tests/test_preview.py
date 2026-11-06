import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for relative in ("modules/preview/src", "modules/storage/src"):
    sys.path.insert(0, str(ROOT / relative))

from PIL import Image  # noqa: E402

from moyu_preview import PreviewError, PreviewProvider  # noqa: E402
from moyu_storage import AssetStore, Storage  # noqa: E402


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.tmp.name) / "data").ensure_layout()
        self.assets = AssetStore(self.storage)
        self.provider = PreviewProvider(self.storage, max_memory_bytes=64 * 1024 * 1024)
        source = Path(self.tmp.name) / "image.png"
        Image.new("RGB", (640, 320), (10, 20, 30)).save(source)
        self.asset = self.assets.register_asset(source, original_name="image.png")

    def tearDown(self):
        self.tmp.cleanup()

    def test_probe(self):
        info = self.provider.probe(self.asset.id)
        self.assertTrue(info["supported"])
        self.assertEqual(info["width"], 640)
        self.assertEqual(info["height"], 320)
        self.assertEqual(info["format"], "png")

    def test_generate_and_cache(self):
        artifact = self.provider.generate(self.asset.id, "thumb")
        self.assertFalse(artifact.cached)
        self.assertTrue(Path(artifact.path).exists())
        with Image.open(artifact.path) as image:
            self.assertLessEqual(image.width, 256)
            self.assertLessEqual(image.height, 256)
            self.assertEqual(image.format, "WEBP")
        first_mtime = Path(artifact.path).stat().st_mtime_ns

        cached = self.provider.generate(self.asset.id, "thumb")
        self.assertTrue(cached.cached)
        self.assertEqual(Path(cached.path).stat().st_mtime_ns, first_mtime)

        view = self.provider.generate(self.asset.id, "view")
        with Image.open(view.path) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertLessEqual(image.width, 1920)

    def test_custom_profile_and_invalid_profile(self):
        artifact = self.provider.generate(
            self.asset.id,
            {"maxWidth": 64, "maxHeight": 64, "format": "png", "quality": 90},
        )
        self.assertEqual(artifact.profile, "custom")
        with Image.open(artifact.path) as image:
            self.assertLessEqual(image.width, 64)
        with self.assertRaises(PreviewError) as ctx:
            self.provider.generate(self.asset.id, "nope")
        self.assertEqual(ctx.exception.code, "profile_unknown")
        with self.assertRaises(PreviewError) as ctx:
            self.provider.generate(self.asset.id, {"maxWidth": 0, "maxHeight": 10})
        self.assertEqual(ctx.exception.code, "profile_invalid")

    def test_memory_limit(self):
        provider = PreviewProvider(self.storage, max_memory_bytes=1024)
        with self.assertRaises(PreviewError) as ctx:
            provider.generate(self.asset.id, "thumb")
        self.assertEqual(ctx.exception.code, "preview_too_large")

    def test_unsupported_media(self):
        source = Path(self.tmp.name) / "clip.mp4"
        source.write_bytes(b"not really mp4")
        asset = self.assets.register_asset(source, original_name="clip.mp4")
        info = self.provider.probe(asset.id)
        self.assertFalse(info["supported"])
        self.assertEqual(info["type"], "video")
        with self.assertRaises(PreviewError) as ctx:
            self.provider.generate(asset.id, "thumb")
        self.assertEqual(ctx.exception.code, "preview_unsupported")

    def test_delete_cache(self):
        artifact = self.provider.generate(self.asset.id, "thumb")
        self.assertTrue(Path(artifact.path).exists())
        self.provider.delete(self.asset.id)
        self.assertFalse(Path(artifact.path).exists())
        with self.assertRaises(PreviewError) as ctx:
            self.provider.probe("missing")
        self.assertEqual(ctx.exception.code, "asset_not_found")


if __name__ == "__main__":
    unittest.main()