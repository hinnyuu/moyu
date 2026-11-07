import json
import sys
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

from moyu_api.preview_client import PreviewClient, PreviewClientError  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path == "/preview/a1/thumb":
            body = b"preview-bytes"
            self.send_response(200)
            self.send_header("Content-Type", "image/webp")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/preview/a1/hls/index.m3u8":
            body = b"#EXTM3U\nsegment_000.ts\n"
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.apple.mpegurl")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/probe/a1":
            body = json.dumps({"supported": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/preview/nope/thumb":
            body = json.dumps({"code": "asset_not_found", "message": "no"}).encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        self.send_response(204)
        self.end_headers()


class PreviewClientTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.client = PreviewClient(f"http://{host}:{port}")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_generate_and_probe(self):
        body, media = self.client.generate("a1", "thumb")
        self.assertEqual(body, b"preview-bytes")
        self.assertEqual(media, "image/webp")
        self.assertTrue(self.client.probe("a1")["supported"])
        playlist, media = self.client.generate_file("a1", "hls", "index.m3u8")
        self.assertIn(b"#EXTM3U", playlist)
        self.assertEqual(media, "application/vnd.apple.mpegurl")
        self.client.purge("a1")

    def test_error_mapping(self):
        with self.assertRaises(PreviewClientError) as ctx:
            self.client.generate("nope", "thumb")
        self.assertEqual(ctx.exception.code, "asset_not_found")

    def test_unreachable(self):
        self.server.shutdown()
        self.server.server_close()
        with self.assertRaises(PreviewClientError) as ctx:
            self.client.probe("a1")
        self.assertEqual(ctx.exception.code, "preview_unreachable")


if __name__ == "__main__":
    unittest.main()
