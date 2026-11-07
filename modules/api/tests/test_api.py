import base64
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


class FakeGatewayAdmin:
    def __init__(self):
        self.token = ""
        self.calls = []

    def rotate_token(self):
        self.token = "plain-token-once"
        self.calls.append("rotate")
        return self.token

    def revoke_token(self):
        self.token = ""
        self.calls.append("revoke")

    def token_metadata(self):
        return {
            "exists": bool(self.token),
            "bytes": len(self.token),
            "modified_at": "2026-11-06T00:00:00+00:00" if self.token else None,
        }

    def reload_cert(self):
        self.calls.append("reload")
        return {"status": "reloaded", "cert_sha256": "deadbeef"}

    def cert_status(self):
        return {"status": "ok", "cert_sha256": "deadbeef"}

    def audit(self, limit=100):
        return [{"action": "rotate", "limit": limit}]


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
        self.gateway = FakeGatewayAdmin()
        self.app = create_app(
            self.storage,
            self.config,
            self.auth,
            gateway_admin=self.gateway,
            tusd_hook_token="hook-token",
        )
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
        self.assertEqual(health.headers["cross-origin-opener-policy"], "same-origin")
        self.assertEqual(health.headers["cross-origin-embedder-policy"], "require-corp")

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

        audit = self.client.get("/api/v1/config/audit").json()
        self.assertEqual(audit[0]["module"], "worker")
        self.assertEqual(audit[0]["action"], "write")
        self.assertEqual(audit[0]["actor"], "api")

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

    def test_gateway_admin_proxy_and_tokens(self):
        csrf = self.login()
        headers = self.csrf_headers(csrf)

        status = self.client.get("/api/v1/admin/gateway/cert/status")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["cert_sha256"], "deadbeef")

        no_csrf = self.client.post("/api/v1/admin/gateway/cert/reload")
        self.assertEqual(no_csrf.status_code, 403)
        reloaded = self.client.post("/api/v1/admin/gateway/cert/reload", headers=headers)
        self.assertEqual(reloaded.status_code, 200)
        self.assertEqual(reloaded.json()["status"], "reloaded")

        rotated = self.client.post("/api/v1/admin/gateway/token/rotate", headers=headers)
        self.assertEqual(rotated.status_code, 201)
        self.assertEqual(rotated.json()["token"], "plain-token-once")
        self.assertTrue(rotated.json()["shown_once"])

        metadata = self.client.get("/api/v1/admin/gateway/token").json()
        self.assertTrue(metadata["exists"])
        self.assertNotIn("token", metadata)

        audit = self.client.get("/api/v1/admin/gateway/token/audit?limit=5").json()
        self.assertEqual(audit[0]["action"], "rotate")
        self.assertEqual(audit[0]["limit"], 5)

        revoked = self.client.delete("/api/v1/admin/gateway/token", headers=headers)
        self.assertEqual(revoked.status_code, 204)
        self.assertFalse(self.client.get("/api/v1/admin/gateway/token").json()["exists"])
        self.assertEqual(self.gateway.calls, ["reload", "rotate", "revoke"])

    def test_tusd_hook(self):
        base = "/api/v1/internal/tusd/hook?token=hook-token"
        denied = self.client.post(
            "/api/v1/internal/tusd/hook?token=nope",
            json={"Type": "pre-create", "Event": {"Upload": {"Size": 1}}},
        )
        self.assertEqual(denied.status_code, 403)

        valid = self.client.post(
            base,
            json={
                "Type": "pre-create",
                "Event": {"Upload": {"Size": 10, "MetaData": {}}},
            },
        )
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.json()["HTTPResponse"]["StatusCode"], 200)

        too_large = self.client.post(
            base,
            json={
                "Type": "pre-create",
                "Event": {"Upload": {"Size": 3_000_000_000, "MetaData": {}}},
            },
        )
        self.assertEqual(too_large.json()["HTTPResponse"]["StatusCode"], 413)

        source = self.storage.data_root / "tusd-upload.bin"
        source.write_bytes(b"tusd-data")
        metadata = {
            "filename": base64.b64encode(b"tusd.bin").decode("ascii"),
            "filetype": base64.b64encode(b"application/octet-stream").decode("ascii"),
        }
        finished = self.client.post(
            base,
            json={
                "Type": "post-finish",
                "Event": {
                    "Upload": {
                        "Size": 9,
                        "MetaData": metadata,
                        "Storage": {"Type": "filestore", "Path": str(source)},
                    }
                },
            },
        )
        self.assertEqual(finished.status_code, 200, finished.text)
        asset_id = finished.json()["HTTPResponse"]["Body"]
        asset = AssetStore(self.storage).get_asset(asset_id)
        self.assertEqual(asset.original_name, "tusd.bin")
        self.assertFalse(source.exists())

    def test_login_rate_limit(self):
        for _ in range(5):
            response = self.client.post(
                "/api/v1/auth/session",
                json={"bootstrap_token": "wrong", "password": "secret-pass"},
            )
            self.assertEqual(response.status_code, 401)
        blocked = self.client.post(
            "/api/v1/auth/session",
            json={"bootstrap_token": BOOTSTRAP, "password": PASSWORD},
        )
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.json()["code"], "rate_limited")

    def test_user_management_and_password_reset(self):
        csrf = self.login()
        headers = self.csrf_headers(csrf)

        created = self.client.post(
            "/api/v1/users",
            json={
                "username": "operator1",
                "password": "operator-pass",
                "role": "operator",
            },
            headers=headers,
        )
        self.assertEqual(created.status_code, 201, created.text)
        users = self.client.get("/api/v1/users").json()
        self.assertIn("operator1", [item["username"] for item in users])

        operator = TestClient(self.app)
        logged = operator.post(
            "/api/v1/auth/session",
            json={"username": "operator1", "password": "operator-pass"},
        )
        self.assertEqual(logged.status_code, 204, logged.text)
        forbidden = operator.get("/api/v1/users")
        self.assertEqual(forbidden.status_code, 403)

        reset = self.client.post(
            "/api/v1/users/operator1/password",
            json={"password": "operator-reset"},
            headers=headers,
        )
        self.assertEqual(reset.status_code, 204, reset.text)
        operator2 = TestClient(self.app)
        self.assertEqual(
            operator2.post(
                "/api/v1/auth/session",
                json={"username": "operator1", "password": "operator-reset"},
            ).status_code,
            204,
        )

        bootstrap_reset = TestClient(self.app).post(
            "/api/v1/auth/password/reset",
            json={"bootstrap_token": BOOTSTRAP, "password": "reset-pass"},
        )
        self.assertEqual(bootstrap_reset.status_code, 204, bootstrap_reset.text)
        admin2 = TestClient(self.app)
        self.assertEqual(
            admin2.post(
                "/api/v1/auth/session", json={"password": "reset-pass"}
            ).status_code,
            204,
        )

        deleted = self.client.delete(
            "/api/v1/users/operator1", headers=headers
        )
        self.assertEqual(deleted.status_code, 204, deleted.text)

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