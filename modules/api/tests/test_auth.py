import os
import stat
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
):
    sys.path.insert(0, str(ROOT / relative))

from moyu_api.auth import (  # noqa: E402
    AuthError,
    AuthManager,
    hash_password,
    verify_password,
)


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.token = self.root / "bootstrap.txt"
        self.token.write_text("boot-token\n", encoding="utf-8")
        self.manager = AuthManager(
            bootstrap_token_file=self.token,
            state_file=self.root / "auth.json",
            secret_file=self.root / "session.secret",
            ttl_seconds=3600,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_password_hash_roundtrip(self):
        encoded = hash_password("correct horse")
        self.assertTrue(verify_password("correct horse", encoded))
        self.assertFalse(verify_password("wrong", encoded))
        self.assertNotIn("correct horse", encoded)

    def test_setup_and_login(self):
        self.assertFalse(self.manager.is_configured())
        session = self.manager.setup("boot-token", "secret-pass")
        self.assertTrue(self.manager.is_configured())
        self.assertEqual(session.username, "admin")
        self.assertTrue(self.manager.verify_session(self.manager.sign_session(session)))

        again = self.manager.login("secret-pass")
        self.assertEqual(again.username, "admin")
        with self.assertRaises(AuthError) as ctx:
            self.manager.login("wrong-pass")
        self.assertEqual(ctx.exception.code, "password_mismatch")
        with self.assertRaises(AuthError) as ctx:
            self.manager.setup("boot-token", "another-pass")
        self.assertEqual(ctx.exception.code, "already_configured")

    def test_setup_rejects_bad_token_and_password(self):
        with self.assertRaises(AuthError) as ctx:
            self.manager.setup("wrong", "secret-pass")
        self.assertEqual(ctx.exception.code, "bootstrap_invalid")
        with self.assertRaises(AuthError) as ctx:
            self.manager.setup("boot-token", "short")
        self.assertEqual(ctx.exception.code, "password_invalid")

    def test_tampered_and_expired_session(self):
        session = self.manager.setup("boot-token", "secret-pass")
        token = self.manager.sign_session(session)
        with self.assertRaises(AuthError) as ctx:
            self.manager.verify_session(token + "x")
        self.assertEqual(ctx.exception.code, "session_invalid")

        expired = AuthManager(
            bootstrap_token_file=self.token,
            state_file=self.root / "auth.json",
            secret_file=self.root / "session.secret",
            ttl_seconds=-1,
        )
        expired_session = expired._issue("admin")
        with self.assertRaises(AuthError) as ctx:
            expired.verify_session(expired.sign_session(expired_session))
        self.assertEqual(ctx.exception.code, "session_expired")

    def test_csrf(self):
        session = self.manager.setup("boot-token", "secret-pass")
        self.assertTrue(self.manager.verify_csrf(session, session.csrf))
        with self.assertRaises(AuthError) as ctx:
            self.manager.verify_csrf(session, "nope")
        self.assertEqual(ctx.exception.code, "csrf_invalid")

    def test_secret_and_state_permissions(self):
        self.manager.setup("boot-token", "secret-pass")
        self.manager.sign_session(self.manager.login("secret-pass"))
        for path in (self.root / "auth.json", self.root / "session.secret"):
            mode = stat.S_IMODE(os.stat(path).st_mode)
            self.assertEqual(mode, 0o600, path)

    def test_login_before_setup(self):
        with self.assertRaises(AuthError) as ctx:
            self.manager.login("secret-pass")
        self.assertEqual(ctx.exception.code, "not_configured")


if __name__ == "__main__":
    unittest.main()