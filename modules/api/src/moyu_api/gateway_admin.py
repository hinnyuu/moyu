"""Client for the gateway internal admin API and its shared token file."""

import datetime as dt
import json
import os
import secrets
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from .token_store import TokenStore


class GatewayAdminError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []

    def to_dict(self):
        return {"code": self.code, "message": self.message, "details": self.details}


def _atomic_write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".moyu-token-", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
        tmp = None
    except OSError as exc:
        raise GatewayAdminError("token_write_failed", f"写入网关 token 失败: {exc}") from exc
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


class GatewayAdminClient:
    def __init__(self, token_file, admin_listen, timeout=5, state_file=None):
        self.token_file = Path(token_file)
        self.base_url = f"http://{admin_listen}"
        self.timeout = timeout
        if state_file:
            self.state_file = Path(state_file)
        else:
            parent = self.token_file.parent
            if parent.name == "secrets":
                parent = parent.parent
            self.state_file = parent / "state" / "gateway_token.db"
        self._token_store = None

    def _store(self):
        if self._token_store is None:
            self._token_store = TokenStore(self.state_file)
        return self._token_store

    def _token(self):
        try:
            token = self.token_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise GatewayAdminError(
                "gateway_token_missing", f"无法读取网关 token: {exc}"
            ) from exc
        if not token:
            raise GatewayAdminError("gateway_token_missing", "网关 token 为空")
        return token

    def _request(self, method, path):
        token = self._token()
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            method=method,
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read()
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = {}
            raise GatewayAdminError(
                payload.get("code", "gateway_admin_error"),
                payload.get("message", f"网关管理 API 返回 {exc.code}"),
            ) from exc
        except (urllib.error.URLError, OSError) as exc:
            raise GatewayAdminError(
                "gateway_unreachable", f"无法连接网关管理 API: {exc}"
            ) from exc
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GatewayAdminError(
                "gateway_admin_error", "网关管理 API 返回非 JSON"
            ) from exc

    def cert_status(self):
        result = self._request("GET", "/admin/cert/status")
        self._store().mark_used("api", "cert_status")
        return result

    def reload_cert(self):
        result = self._request("POST", "/admin/cert/reload")
        self._store().mark_used("api", "cert_reload")
        return result

    def token_metadata(self):
        if not self.token_file.exists():
            base = {"exists": False, "bytes": 0, "modified_at": None}
        else:
            stat = self.token_file.stat()
            base = {
                "exists": True,
                "bytes": stat.st_size,
                "modified_at": dt.datetime.fromtimestamp(
                    stat.st_mtime, tz=dt.timezone.utc
                ).isoformat(),
            }
        base.update(self._store().metadata())
        return base

    def rotate_token(self, actor="api"):
        token = secrets.token_urlsafe(32)
        _atomic_write(self.token_file, token)
        self._store().rotate(token, actor)
        return token

    def revoke_token(self, actor="api"):
        _atomic_write(self.token_file, "")
        self._store().revoke(actor)

    def audit(self, limit=100):
        return self._store().audit(limit)
