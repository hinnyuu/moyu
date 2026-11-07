import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for relative in ("modules/preview/src", "modules/storage/src"):
    sys.path.insert(0, str(ROOT / relative))

from fastapi.testclient import TestClient
from PIL import Image

from moyu_preview.service import create_preview_app
from moyu_storage import AssetStore, Storage


class PreviewServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.storage = Storage(root / "data").ensure_layout()
        buffer = io.BytesIO()
        Image.new("RGB", (160, 90), (1, 2, 3)).save(buffer, format="PNG")
        source = root / "image.png"
        source.write_bytes(buffer.getvalue())
        self.asset = AssetStore(self.storage).register_asset(source, original_name="image.png")
        app = create_preview_app(
            self.storage,
            {
                "cacheDir": str(root / "data" / "preview"),
                "concurrency": 1,
                "maxMemoryBytes": 64 * 1024 * 1024,
                "timeoutSeconds": 30,
            },
        )
        self.client = TestClient(app)

    def tearDown(self):
        self.tmp.cleanup()

    def test_health_probe_preview_purge(self):
        self.assertEqual(self.client.get("/healthz").status_code, 200)
        probe = self.client.get(f"/probe/{self.asset.id}")
        self.assertEqual(probe.status_code, 200)
        self.assertTrue(probe.json()["supported"])

        preview = self.client.get(f"/preview/{self.asset.id}/thumb")
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(preview.headers["content-type"], "image/webp")
        with Image.open(io.BytesIO(preview.content)) as image:
            self.assertLessEqual(image.width, 256)

        purge = self.client.post(f"/purge/{self.asset.id}")
        self.assertEqual(purge.status_code, 204)

    def test_missing_asset(self):
        response = self.client.get("/preview/nope/thumb")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "asset_not_found")

    def test_unknown_profile(self):
        response = self.client.get(f"/preview/{self.asset.id}/nope")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "profile_unknown")


if __name__ == "__main__":
    unittest.main()
