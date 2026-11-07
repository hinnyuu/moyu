#!/usr/bin/env python3
"""Verify upload sessions survive an API process restart."""

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATHS = [
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
]
for relative in MODULE_PATHS:
    sys.path.insert(0, str(ROOT / relative))

import httpx  # noqa: E402

from moyu_config import ConfigProvider  # noqa: E402

PASSWORD = "restart-secret-pass"
BOOTSTRAP = "restart-boot-token"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    base = Path(tempfile.mkdtemp(prefix="moyu-restart-"))
    config_dir = base / "config"
    data_dir = base / "data"
    secrets = base / "secrets"
    secrets.mkdir(parents=True)
    token_file = secrets / "bootstrap_token"
    token_file.write_text(BOOTSTRAP + "\n", encoding="utf-8")

    provider = ConfigProvider(config_dir)
    effective = provider.load()
    provider.write(
        "storage", {"dataRoot": str(data_dir)}, revision=effective.revisions["storage"]
    )
    provider.write(
        "preview",
        {"cacheDir": str(data_dir / "preview")},
        revision=effective.revisions["preview"],
    )

    port = free_port()
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(str(ROOT / path) for path in MODULE_PATHS),
        "MOYU_CONFIG_DIR": str(config_dir),
        "MOYU_API_LISTEN": f"127.0.0.1:{port}",
        "MOYU_BOOTSTRAP_TOKEN_FILE": str(token_file),
        "MOYU_SESSION_STATE_FILE": str(config_dir / "secrets" / "session-state.json"),
        "MOYU_SESSION_SECRET_FILE": str(config_dir / "secrets" / "session.secret"),
        "PYTHONUNBUFFERED": "1",
    }
    log = open(base / "api.log", "w", encoding="utf-8")
    process = None
    client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=20)

    def start_api():
        return subprocess.Popen(
            [sys.executable, "-m", "moyu_api"], env=env, stdout=log, stderr=log
        )

    def wait_health():
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                if client.get("/api/v1/health").status_code == 200:
                    return
            except Exception:
                pass
            time.sleep(0.3)
        raise RuntimeError("API 未启动")

    def login():
        response = client.post(
            "/api/v1/auth/session",
            json={"bootstrap_token": BOOTSTRAP, "password": PASSWORD},
        )
        if response.status_code == 400:
            response = client.post(
                "/api/v1/auth/session", json={"password": PASSWORD}
            )
        assert response.status_code == 204, response.text
        return client.get("/api/v1/auth/session").json()["csrf"]

    try:
        process = start_api()
        wait_health()
        csrf = login()
        headers = {
            "X-CSRF-Token": csrf,
            "Content-Type": "application/offset+octet-stream",
        }
        created = client.post(
            "/api/v1/uploads",
            json={"filename": "resume.bin", "size": 10},
            headers={"X-CSRF-Token": csrf},
        )
        assert created.status_code == 201, created.text
        upload_id = created.json()["id"]

        first = client.patch(
            f"/api/v1/uploads/{upload_id}",
            content=b"0123",
            headers={**headers, "Upload-Offset": "0"},
        )
        assert first.status_code == 204, first.text

        process.terminate()
        process.wait(timeout=15)
        process = start_api()
        wait_health()
        csrf = login()
        headers["X-CSRF-Token"] = csrf

        resumed = client.get(f"/api/v1/uploads/{upload_id}")
        assert resumed.status_code == 200, resumed.text
        assert resumed.json()["offset"] == 4, resumed.text

        second = client.patch(
            f"/api/v1/uploads/{upload_id}",
            content=b"456789",
            headers={**headers, "Upload-Offset": "4"},
        )
        assert second.status_code == 204, second.text
        finished = client.post(
            f"/api/v1/uploads/{upload_id}/finish",
            headers={"X-CSRF-Token": csrf},
        )
        assert finished.status_code == 201, finished.text
        asset = finished.json()
        payload = client.get(f"/api/v1/assets/{asset['id']}/download").content
        assert payload == b"0123456789"
        print("PASS")
        print(f"asset={asset['id']} offset_after_restart=4 bytes={len(payload)}")
    except Exception:
        print("FAIL")
        print((base / "api.log").read_text(encoding="utf-8")[-4000:])
        raise
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        client.close()
        log.close()


if __name__ == "__main__":
    main()
