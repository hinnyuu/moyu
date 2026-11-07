"""Session authentication, users, password reset and CSRF.

Design:
- bootstrap token enables first-run setup and password reset;
- passwords use PBKDF2-HMAC-SHA256;
- session cookie is a signed JSON payload (HMAC-SHA256) with role;
- CSRF token is bound to the signed payload and mirrored in a readable cookie.
"""

import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
from dataclasses import dataclass
from pathlib import Path

PBKDF2_ITERATIONS = 210_000
PASSWORD_MIN_LENGTH = 8
SESSION_VERSION = 1
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")
ROLES = {"admin", "operator"}


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
    role: str
    csrf: str
    issued_at: int
    expires_at: int

    def to_dict(self):
        return {
            "username": self.username,
            "role": self.role,
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
            state = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AuthError("state_invalid", f"认证状态文件损坏: {exc}") from exc
        if "users" not in state and "admin" in state:
            admin = dict(state["admin"])
            admin.setdefault("role", "admin")
            state["users"] = {"admin": admin}
        return state

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

    def _users(self, state=None):
        state = self._read_state() if state is None else state
        return state.get("users") or {}

    def is_configured(self):
        return bool(self._users())

    def _bootstrap_token(self):
        try:
            return self.bootstrap_token_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise AuthError("bootstrap_missing", f"无法读取 bootstrap token: {exc}") from exc

    def _verify_bootstrap(self, token):
        expected = self._bootstrap_token()
        if not expected or not hmac.compare_digest(str(token), expected):
            raise AuthError("bootstrap_invalid", "bootstrap token 不正确")

    def _validate_password(self, password):
        if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH:
            raise AuthError(
                "password_invalid", f"密码至少 {PASSWORD_MIN_LENGTH} 个字符"
            )

    def setup(self, bootstrap_token, password, username="admin"):
        if self.is_configured():
            raise AuthError("already_configured", "管理员已初始化")
        self._validate_password(password)
        self._verify_bootstrap(bootstrap_token)
        if not USERNAME_RE.match(str(username)):
            raise AuthError("username_invalid", "用户名只能是 1-32 位字母数字._-")
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        self._write_state(
            {
                "version": SESSION_VERSION,
                "users": {
                    username: {
                        "username": username,
                        "password": hash_password(password),
                        "role": "admin",
                        "created_at": now,
                    }
                },
            }
        )
        return self._issue(username, "admin")

    def login(self, password, username="admin"):
        users = self._users()
        if not users:
            raise AuthError("not_configured", "管理员尚未初始化")
        user = users.get(str(username))
        if user is None:
            raise AuthError("password_mismatch", "用户名或密码不正确")
        if not verify_password(str(password), user.get("password", "")):
            raise AuthError("password_mismatch", "用户名或密码不正确")
        return self._issue(user.get("username", username), user.get("role", "operator"))

    def reset_password(self, bootstrap_token, password, username="admin"):
        self._validate_password(password)
        self._verify_bootstrap(bootstrap_token)
        state = self._read_state()
        users = state.setdefault("users", {})
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        user = users.get(username)
        if user is None:
            user = {
                "username": username,
                "role": "admin",
                "created_at": now,
            }
            users[username] = user
        user["password"] = hash_password(password)
        self._write_state(state)
        return self._issue(username, user.get("role", "admin"))

    def list_users(self):
        return [
            {
                "username": name,
                "role": user.get("role", "operator"),
                "created_at": user.get("created_at"),
            }
            for name, user in sorted(self._users().items())
        ]

    def _require_admin(self, actor):
        user = self._users().get(actor)
        if user is None or user.get("role") != "admin":
            raise AuthError("forbidden", "需要管理员权限")

    def create_user(self, actor, username, password, role="operator"):
        self._require_admin(actor)
        if not USERNAME_RE.match(str(username)):
            raise AuthError("username_invalid", "用户名只能是 1-32 位字母数字._-")
        if role not in ROLES:
            raise AuthError("role_invalid", "角色只能是 admin/operator")
        self._validate_password(password)
        state = self._read_state()
        users = state.setdefault("users", {})
        if username in users:
            raise AuthError("user_exists", "用户已存在")
        users[username] = {
            "username": username,
            "password": hash_password(password),
            "role": role,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        self._write_state(state)
        return {"username": username, "role": role}

    def delete_user(self, actor, username):
        self._require_admin(actor)
        if username == actor:
            raise AuthError("forbidden", "不能删除当前登录用户")
        state = self._read_state()
        users = state.setdefault("users", {})
        user = users.get(username)
        if user is None:
            raise AuthError("user_not_found", "用户不存在")
        admins = [item for item in users.values() if item.get("role") == "admin"]
        if user.get("role") == "admin" and len(admins) <= 1:
            raise AuthError("last_admin", "不能删除最后一个管理员")
        del users[username]
        self._write_state(state)

    def change_password(self, actor, username, new_password, old_password=None):
        self._validate_password(new_password)
        users = self._users()
        user = users.get(username)
        if user is None:
            raise AuthError("user_not_found", "用户不存在")
        if actor != username:
            self._require_admin(actor)
        elif old_password is not None:
            if not verify_password(str(old_password), user.get("password", "")):
                raise AuthError("password_mismatch", "原密码不正确")
        else:
            raise AuthError("password_mismatch", "修改自己的密码需要原密码")
        state = self._read_state()
        state["users"][username]["password"] = hash_password(new_password)
        self._write_state(state)

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

    def _issue(self, username, role):
        now = int(dt.datetime.now(dt.timezone.utc).timestamp())
        return Session(
            username=username,
            role=role,
            csrf=_b64(secrets.token_bytes(24)),
            issued_at=now,
            expires_at=now + self.ttl_seconds,
        )

    def sign_session(self, session):
        payload = {
            "v": SESSION_VERSION,
            "sub": session.username,
            "role": session.role,
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
            role=str(payload.get("role", "admin")),
            csrf=str(payload.get("csrf")),
            issued_at=int(payload.get("iat", 0)),
            expires_at=int(payload.get("exp", 0)),
        )

    def verify_csrf(self, session, token):
        if not token or not hmac.compare_digest(str(token), session.csrf):
            raise AuthError("csrf_invalid", "CSRF token 不正确")
        return True

    def set_cookies(self, response, session):
        max_age = max(
            0, session.expires_at - int(dt.datetime.now(dt.timezone.utc).timestamp())
        )
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
