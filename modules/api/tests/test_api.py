import io
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for relative in (
    "modules/api/src",
    "modules/config/src",
    "modules/storage/src",
    "modules/uploads/src",
    "modules/preview/src",
    "modules/media-metadata/src",
    "modules/archive-zip/src",
    "modules/pipeline/src",
    "modules/core-time/python",
    "modules/worker/src",
):
    sys.path.insert(0, str(ROOT / relative))

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from moyu_api import AuthManager, create_app  # noqa: E402
from moyu_config import ConfigProvider  # noqa: E402
from moyu_storage import AssetStore, Storage  # noqa: E402
from moyu_worker import Worker  # noqa: E402

PASSWORD = "secret-pass"
BOOTSTRAP = "boot-token"


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.storage = Storage(root / "data").ensure_layout()
        self.config = ConfigProvider(root / "config")
        loaded = self.config.load()
        self.config.write(
            "preview",
            {"cacheDir": str(self.storage.preview_dir)},
            revision=loaded.revisions["preview"],
        )
        token_file = root / "bootstrap.txt"
        token_file.write_text(BOOTSTRAP + "\n", encoding="utf-8")
        self.auth = AuthManager(
            bootstrap_token_file=token_file,
            state_file=root / "auth.json",
            secret_file=root / "session.secret",
            ttl_seconds=3600,
        )
        self.app = create_app(self.storage, self.config, self.auth)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.tmp.cleanup()

    def login(self):
        response = self.client.post(
            "/api/v1/auth/session",
            json={"bootstrap_token": BOOTSTRAP, "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 204, response.text)
        info = self.client.get("/api/v1/auth/session")
        self.assertEqual(info.status_code, 200, info.text)
        return info.json()["csrf"]

    def csrf_headers(self, csrf):
        return {"X-CSRF-Token": csrf}

    def make_asset(self, name="frame.bin", data=b"frame-data"):
        source = Path(self.tmp.name) / name
        source.write_bytes(data)
        return AssetStore(self.storage).register_asset(source, original_name=name)

    def test_health_and_auth_flow(self):
        health = self.client.get("/api/v1/health")
        self.assertEqual(health.status_code, 200)
        self.assertFalse(health.json()["configured"])

        unauthenticated = self.client.get("/api/v1/config")
        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(unauthenticated.json()["code"], "auth_required")

        csrf = self.login()
        self.assertEqual(self.client.get("/api/v1/auth/session").json()["username"], "admin")

        without_csrf = self.client.delete("/api/v1/auth/session")
        self.assertEqual(without_csrf.status_code, 403)

        again = self.client.post(
            "/api/v1/auth/session", json={"password": PASSWORD}
        )
        self.assertEqual(again.status_code, 204, again.text)
        with self.assertRaises(Exception):
            self.client.post(
                "/api/v1/auth/session", json={"password": "wrong-password"}
            ).raise_for_status()

    def test_config_read_write_and_revision(self):
        csrf = self.login()
        headers = self.csrf_headers(csrf)
        snapshot = self.client.get("/api/v1/config").json()
        self.assertIn("global", snapshot)
        module = self.client.get("/api/v1/config/worker").json()

        rejected = self.client.put(
            "/api/v1/config/worker",
            json={"patch": {"concurrency": 4}, "revision": module["revision"]},
        )
        self.assertEqual(rejected.status_code, 403)

        saved = self.client.put(
            "/api/v1/config/worker",
            json={"patch": {"concurrency": 4}, "revision": module["revision"]},
            headers=headers,
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["config"]["concurrency"], 4)

        stale = self.client.put(
            "/api/v1/config/worker",
            json={"patch": {"concurrency": 2}, "revision": module["revision"]},
            headers=headers,
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["code"], "revision_conflict")

    def test_upload_download_and_preview(self):
        csrf = self.login()
        headers = self.csrf_headers(csrf)

        created = self.client.post(
            "/api/v1/uploads",
            json={"filename": "plain.bin", "size": 3},
            headers=headers,
        )
        self.assertEqual(created.status_code, 201, created.text)
        upload_id = created.json()["id"]
        chunk = self.client.patch(
            f"/api/v1/uploads/{upload_id}",
            content=b"abc",
            headers={
                **headers,
                "Upload-Offset": "0",
                "Content-Type": "application/offset+octet-stream",
            },
        )
        self.assertEqual(chunk.status_code, 204, chunk.text)
        self.assertEqual(chunk.headers["upload-offset"], "3")
        finished = self.client.post(
            f"/api/v1/uploads/{upload_id}/finish", headers=headers
        )
        self.assertEqual(finished.status_code, 201, finished.text)
        asset = finished.json()
        download = self.client.get(f"/api/v1/assets/{asset['id']}/download")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.content, b"abc")

        buffer = io.BytesIO()
        Image.new("RGB", (128, 64), (4, 5, 6)).save(buffer, format="PNG")
        png = buffer.getvalue()
        created = self.client.post(
            "/api/v1/uploads",
            json={"filename": "image.png", "size": len(png), "media_type": "image/png"},
            headers=headers,
        )
        upload_id = created.json()["id"]
        chunk = self.client.patch(
            f"/api/v1/uploads/{upload_id}",
            content=png,
            headers={
                **headers,
                "Upload-Offset": "0",
                "Content-Type": "application/offset+octet-stream",
            },
        )
        self.assertEqual(chunk.status_code, 204, chunk.text)
        image_asset = self.client.post(
            f"/api/v1/uploads/{upload_id}/finish", headers=headers
        ).json()

        preview = self.client.get(f"/api/v1/previews/{image_asset['id']}/thumb")
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(preview.headers["content-type"], "image/webp")
        with Image.open(io.BytesIO(preview.content)) as image:
            self.assertLessEqual(image.width, 256)

    def test_job_flow_with_worker(self):
        csrf = self.login()
        headers = self.csrf_headers(csrf)
        asset = self.make_asset()
        target = int(time.time()) + 3600

        created = self.client.post(
            "/api/v1/jobs",
            json={
                "inputs": [{"asset_id": asset.id, "arcname": "frames/frame.bin"}],
                "target_epoch": target,
                "timezone": "UTC",
                "output_name": "delivery.zip",
            },
            headers=headers,
        )
        self.assertEqual(created.status_code, 202, created.text)
        job = created.json()
        self.assertEqual(job["status"], "queued")
        not_ready = self.client.get(f"/api/v1/jobs/{job['id']}/download")
        self.assertEqual(not_ready.status_code, 409)
        self.assertEqual(not_ready.json()["code"], "job_not_ready")

        result = Worker(self.storage).run_once()
        self.assertEqual(result.status, "succeeded")

        finished = self.client.get(f"/api/v1/jobs/{job['id']}")
        self.assertEqual(finished.status_code, 200)
        self.assertEqual(finished.json()["status"], "succeeded")
        self.assertEqual(finished.json()["progress"], 100)

        events = self.client.get(f"/api/v1/jobs/{job['id']}/events")
        self.assertEqual(events.status_code, 200)
        self.assertIn("event: end", events.text)

        listed = self.client.get("/api/v1/jobs?status=succeeded").json()
        self.assertEqual([item["id"] for item in listed], [job["id"]])

        download = self.client.get(f"/api/v1/jobs/{job['id']}/download")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.headers["content-type"], "application/zip")
        self.assertTrue(download.content.startswith(b"PK"))

    def test_cancel_and_errors(self):
        csrf = self.login()
        headers = self.csrf_headers(csrf)
        asset = self.make_asset()
        created = self.client.post(
            "/api/v1/jobs",
            json={
                "inputs": [{"asset_id": asset.id, "arcname": "a.bin"}],
                "target_epoch": int(time.time()) + 3600,
            },
            headers=headers,
        ).json()

        without_csrf = self.client.delete(f"/api/v1/jobs/{created['id']}")
        self.assertEqual(without_csrf.status_code, 403)
        canceled = self.client.delete(
            f"/api/v1/jobs/{created['id']}", headers=headers
        )
        self.assertEqual(canceled.status_code, 202)
        self.assertEqual(canceled.json()["status"], "canceled")

        missing = self.client.get("/api/v1/jobs/nope")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["code"], "job_not_found")
        missing_asset = self.client.get("/api/v1/assets/nope/download")
        self.assertEqual(missing_asset.status_code, 404)
        self.assertEqual(missing_asset.json()["code"], "asset_not_found")

    def test_gateway_admin_not_implemented(self):
        self.login()
        response = self.client.get("/api/v1/admin/gateway/cert/status")
        self.assertEqual(response.status_code, 501)
        self.assertEqual(response.json()["code"], "gateway_admin_unavailable")

    def test_request_size_limit(self):
        csrf = self.login()
        body = b"x" * (1024 * 1024 + 1)
        response = self.client.post(
            "/api/v1/jobs",
            content=body,
            headers={
                **self.csrf_headers(csrf),
                "Content-Type": "application/json",
            },
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["code"], "request_too_large")


if __name__ == "__main__":
    unittest.main()