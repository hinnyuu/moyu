import json
import os
import stat
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
):
    sys.path.insert(0, str(ROOT / relative))

from moyu_api.gateway_admin import GatewayAdminClient, GatewayAdminError  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    token = "admin-token"

    def log_message(self, *_args):
        pass

    def _send(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _auth(self):
        return self.headers.get("Authorization") == f"Bearer {self.token}"

    def do_GET(self):
        if not self._auth():
            self._send(401, {"code": "unauthorized", "message": "no"})
        elif self.path == "/admin/cert/status":
            self._send(200, {"status": "ok", "cert_sha256": "abc"})
        else:
            self._send(404, {"code": "not_found", "message": "no"})

    def do_POST(self):
        if not self._auth():
            self._send(401, {"code": "unauthorized", "message": "no"})
        elif self.path == "/admin/cert/reload":
            self._send(200, {"status": "reloaded", "cert_sha256": "def"})
        else:
            self._send(404, {"code": "not_found", "message": "no"})


class GatewayAdminTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.token_file = Path(self.tmp.name) / "gateway.token"
        self.token_file.write_text("admin-token\n", encoding="utf-8")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.client = GatewayAdminClient(self.token_file, f"{host}:{port}")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def test_proxy_calls(self):
        self.assertEqual(self.client.cert_status()["cert_sha256"], "abc")
        self.assertEqual(self.client.reload_cert()["status"], "reloaded")

    def test_rotate_metadata_revoke(self):
        token = self.client.rotate_token()
        self.assertTrue(token)
        metadata = self.client.token_metadata()
        self.assertTrue(metadata["exists"])
        self.assertEqual(metadata["bytes"], len(token))
        mode = stat.S_IMODE(os.stat(self.token_file).st_mode)
        self.assertEqual(mode, 0o600)

        self.client.revoke_token()
        self.assertEqual(self.token_file.read_text(encoding="utf-8"), "")
        self.assertEqual(self.client.token_metadata()["bytes"], 0)

    def test_missing_token_fails_before_http(self):
        self.token_file.write_text("", encoding="utf-8")
        with self.assertRaises(GatewayAdminError) as ctx:
            self.client.cert_status()
        self.assertEqual(ctx.exception.code, "gateway_token_missing")

    def test_unreachable(self):
        self.server.shutdown()
        self.server.server_close()
        with self.assertRaises(GatewayAdminError) as ctx:
            self.client.cert_status()
        self.assertEqual(ctx.exception.code, "gateway_unreachable")


if __name__ == "__main__":
    unittest.main()
