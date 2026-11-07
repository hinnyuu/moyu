#!/usr/bin/env python3
"""Process-level end-to-end smoke test (no Podman required).

Starts the API and worker entrypoints as subprocesses, uploads a PNG, creates a
pack job, waits for completion and verifies the downloaded ZIP plus manifest.
"""

import hashlib
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
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
from PIL import Image  # noqa: E402

from moyu_config import ConfigProvider  # noqa: E402

PASSWORD = "e2e-secret-pass"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def build_png():
    buffer = io.BytesIO()
    Image.new("RGB", (160, 90), (30, 80, 150)).save(buffer, format="PNG")
    return buffer.getvalue()


def main():
    base = Path(tempfile.mkdtemp(prefix="moyu-e2e-"))
    config_dir = base / "config"
    data_dir = base / "data"
    secrets = base / "secrets"
    secrets.mkdir(parents=True)
    token_file = secrets / "bootstrap_token"
    token_file.write_text("e2e-boot-token\n", encoding="utf-8")

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
    }

    api_log = open(base / "api.log", "w", encoding="utf-8")
    worker_log = open(base / "worker.log", "w", encoding="utf-8")
    api = subprocess.Popen(
        [sys.executable, "-m", "moyu_api"], env=env, stdout=api_log, stderr=api_log
    )
    worker = subprocess.Popen(
        [sys.executable, "-m", "moyu_worker"], env=env, stdout=worker_log, stderr=worker_log
    )

    try:
        client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=20)
        deadline = time.time() + 30
        while True:
            try:
                if client.get("/api/v1/health").status_code == 200:
                    break
            except Exception:
                pass
            if time.time() > deadline:
                raise RuntimeError("API 未在 30 秒内启动")
            time.sleep(0.3)

        response = client.post(
            "/api/v1/auth/session",
            json={"bootstrap_token": "e2e-boot-token", "password": PASSWORD},
        )
        assert response.status_code == 204, response.text
        session = client.get("/api/v1/auth/session").json()
        headers = {"X-CSRF-Token": session["csrf"]}

        png = build_png()
        created = client.post(
            "/api/v1/uploads",
            json={"filename": "frame.png", "size": len(png), "media_type": "image/png"},
            headers=headers,
        )
        assert created.status_code == 201, created.text
        upload_id = created.json()["id"]
        chunk = client.patch(
            f"/api/v1/uploads/{upload_id}",
            content=png,
            headers={
                **headers,
                "Upload-Offset": "0",
                "Content-Type": "application/offset+octet-stream",
            },
        )
        assert chunk.status_code == 204, chunk.text
        finished = client.post(f"/api/v1/uploads/{upload_id}/finish", headers=headers)
        assert finished.status_code == 201, finished.text
        asset = finished.json()
        before = client.get(f"/api/v1/assets/{asset['id']}/download").content
        assert before == png

        target = int(time.time()) + 600
        job_response = client.post(
            "/api/v1/jobs",
            json={
                "inputs": [{"asset_id": asset["id"], "arcname": "frames/frame.png"}],
                "target_epoch": target,
                "timezone": "UTC",
                "output_name": "delivery.zip",
            },
            headers=headers,
        )
        assert job_response.status_code == 202, job_response.text
        job = job_response.json()

        deadline = time.time() + 60
        while True:
            current = client.get(f"/api/v1/jobs/{job['id']}").json()
            if current["status"] in ("succeeded", "failed", "canceled"):
                break
            if time.time() > deadline:
                raise RuntimeError("任务未在 60 秒内完成")
            time.sleep(0.4)
        assert current["status"] == "succeeded", current
        assert current["progress"] == 100

        download = client.get(f"/api/v1/jobs/{job['id']}/download")
        assert download.status_code == 200, download.text
        archive = base / "delivery.zip"
        archive.write_bytes(download.content)

        with zipfile.ZipFile(archive) as zf:
            assert zf.namelist() == ["frames/frame.png"]
            info = zf.infolist()[0]
            assert abs(info.date_time[3] - time.gmtime(target).tm_hour) <= 1
            patched = zf.read("frames/frame.png")
            with Image.open(io.BytesIO(patched)) as image:
                image.load()

        after = client.get(f"/api/v1/assets/{asset['id']}/download").content
        assert after == png, "源资产被修改"

        manifest_path = data_dir / "jobs" / job["id"] / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        assert manifest["archive_sha256"] == digest
        assert manifest["entries"][0]["metadata"]["format"] == "png"

        print("PASS")
        print(f"job={job['id']} entries={len(manifest['entries'])} bytes={archive.stat().st_size}")
        print(f"archive={archive}")
    except Exception:
        print("FAIL")
        for name in ("api.log", "worker.log"):
            path = base / name
            print(f"--- {name} ---")
            print(path.read_text(encoding="utf-8")[-4000:])
        raise
    finally:
        for process in (worker, api):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        api_log.close()
        worker_log.close()


if __name__ == "__main__":
    main()
