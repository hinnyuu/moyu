"""Session authentication for the API.

Design:

- bootstrap token file enables first-run setup;
- admin password is stored as PBKDF2-HMAC-SHA256;
- session cookie is a signed JSON payload (HMAC-SHA256);
- a CSRF token is bound to the signed payload and mirrored in a readable cookie.
"""

import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import tempfile
from dataclasses import dataclass
from pathlib import Path

PBKDF2_ITERATIONS = 210_000
PASSWORD_MIN_LENGTH = 8
SESSION_VERSION = 1


class AuthError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []

    def to_dict(self):
        return {"code": self.code, "message": self.message, "details": self.details}


@dataclass
class Session:
    username: str
    csrf: str
    issued_at: int
    expires_at: int

    def to_dict(self):
        return {
            "username": self.username,
            "csrf": self.csrf,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def hash_password(password: str, iterations=PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        expected = _unb64(digest)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _unb64(salt), int(iterations)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class AuthManager:
    def __init__(
        self,
        bootstrap_token_file,
        state_file,
        secret_file,
        cookie_name="moyu_session",
        csrf_cookie_name="moyu_csrf",
        ttl_seconds=86400,
        cookie_secure=False,
    ):
        self.bootstrap_token_file = Path(bootstrap_token_file)
        self.state_file = Path(state_file)
        self.secret_file = Path(secret_file)
        self.cookie_name = cookie_name
        self.csrf_cookie_name = csrf_cookie_name
        self.ttl_seconds = int(ttl_seconds)
        self.cookie_secure = bool(cookie_secure)

    def _read_state(self):
        if not self.state_file.exists():
            return {}
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AuthError("state_invalid", f"认证状态文件损坏: {exc}") from exc

    def _write_state(self, state):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            prefix=".moyu-auth-", suffix=".part", dir=self.state_file.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(state, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.state_file)
            tmp = None
        except OSError as exc:
            raise AuthError("state_write_failed", f"写入认证状态失败: {exc}") from exc
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    def is_configured(self):
        return bool(self._read_state().get("admin"))

    def _bootstrap_token(self):
        try:
            return self.bootstrap_token_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise AuthError("bootstrap_missing", f"无法读取 bootstrap token: {exc}") from exc

    def setup(self, bootstrap_token, password):
        if self.is_configured():
            raise AuthError("already_configured", "管理员已初始化")
        if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH:
            raise AuthError(
                "password_invalid", f"密码至少 {PASSWORD_MIN_LENGTH} 个字符"
            )
        expected = self._bootstrap_token()
        if not expected or not hmac.compare_digest(str(bootstrap_token), expected):
            raise AuthError("bootstrap_invalid", "bootstrap token 不正确")
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        self._write_state(
            {
                "version": SESSION_VERSION,
                "admin": {
                    "username": "admin",
                    "password": hash_password(password),
                    "created_at": now,
                },
            }
        )
        return self._issue("admin")

    def login(self, password):
        state = self._read_state()
        admin = state.get("admin")
        if not admin:
            raise AuthError("not_configured", "管理员尚未初始化")
        if not verify_password(str(password), admin.get("password", "")):
            raise AuthError("password_mismatch", "用户名或密码不正确")
        return self._issue(admin.get("username", "admin"))

    def _secret(self):
        try:
            return self.secret_file.read_bytes()
        except OSError:
            pass
        secret = secrets.token_bytes(32)
        self.secret_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd, tmp = tempfile.mkstemp(
                prefix=".moyu-secret-", suffix=".part", dir=self.secret_file.parent
            )
            with os.fdopen(fd, "wb") as handle:
                handle.write(secret)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.secret_file)
        except OSError as exc:
            raise AuthError("secret_write_failed", f"无法生成会话密钥: {exc}") from exc
        return secret

    def _issue(self, username):
        now = int(dt.datetime.now(dt.timezone.utc).timestamp())
        return Session(
            username=username,
            csrf=_b64(secrets.token_bytes(24)),
            issued_at=now,
            expires_at=now + self.ttl_seconds,
        )

    def sign_session(self, session):
        payload = {
            "v": SESSION_VERSION,
            "sub": session.username,
            "csrf": session.csrf,
            "iat": session.issued_at,
            "exp": session.expires_at,
        }
        body = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = hmac.new(self._secret(), body.encode("ascii"), hashlib.sha256).digest()
        return f"{body}.{_b64(signature)}"

    def verify_session(self, token):
        if not token or "." not in token:
            raise AuthError("session_invalid", "会话无效")
        body, signature = token.rsplit(".", 1)
        expected = hmac.new(
            self._secret(), body.encode("ascii"), hashlib.sha256
        ).digest()
        try:
            provided = _unb64(signature)
        except (ValueError, TypeError):
            raise AuthError("session_invalid", "会话无效")
        if not hmac.compare_digest(provided, expected):
            raise AuthError("session_invalid", "会话无效")
        try:
            payload = json.loads(_unb64(body))
        except (ValueError, TypeError):
            raise AuthError("session_invalid", "会话无效")
        now = int(dt.datetime.now(dt.timezone.utc).timestamp())
        if payload.get("v") != SESSION_VERSION or int(payload.get("exp", 0)) <= now:
            raise AuthError("session_expired", "会话已过期")
        return Session(
            username=str(payload.get("sub")),
            csrf=str(payload.get("csrf")),
            issued_at=int(payload.get("iat", 0)),
            expires_at=int(payload.get("exp", 0)),
        )

    def verify_csrf(self, session, token):
        if not token or not hmac.compare_digest(str(token), session.csrf):
            raise AuthError("csrf_invalid", "CSRF token 不正确")
        return True

    def set_cookies(self, response, session):
        max_age = max(0, session.expires_at - int(dt.datetime.now(dt.timezone.utc).timestamp()))
        response.set_cookie(
            self.cookie_name,
            self.sign_session(session),
            max_age=max_age,
            httponly=True,
            samesite="lax",
            secure=self.cookie_secure,
            path="/",
        )
        response.set_cookie(
            self.csrf_cookie_name,
            session.csrf,
            max_age=max_age,
            httponly=False,
            samesite="lax",
            secure=self.cookie_secure,
            path="/",
        )

    def clear_cookies(self, response):
        response.delete_cookie(self.cookie_name, path="/")
        response.delete_cookie(self.csrf_cookie_name, path="/")