"""HTTP client for the internal preview service."""

import json
import urllib.error
import urllib.request


class PreviewClientError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []

    def to_dict(self):
        return {"code": self.code, "message": self.message, "details": self.details}


class PreviewClient:
    def __init__(self, base_url, timeout=60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, path, method="GET"):
        request = urllib.request.Request(f"{self.base_url}{path}", method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read(), response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            body = exc.read()
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = {}
            raise PreviewClientError(
                payload.get("code", "preview_service_error"),
                payload.get("message", f"预览服务返回 {exc.code}"),
                payload.get("details", []),
            ) from exc
        except (urllib.error.URLError, OSError) as exc:
            raise PreviewClientError(
                "preview_unreachable", f"无法连接预览服务: {exc}"
            ) from exc

    def health(self):
        body, _ = self._request("/healthz")
        return json.loads(body.decode("utf-8"))

    def probe(self, asset_id):
        body, _ = self._request(f"/probe/{asset_id}")
        return json.loads(body.decode("utf-8"))

    def generate(self, asset_id, profile):
        body, content_type = self._request(f"/preview/{asset_id}/{profile}")
        return body, content_type

    def generate_file(self, asset_id, profile, filename):
        body, content_type = self._request(
            f"/preview/{asset_id}/{profile}/{filename}"
        )
        return body, content_type

    def purge(self, asset_id):
        self._request(f"/purge/{asset_id}", method="POST")
