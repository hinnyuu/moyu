"""SQLite metadata and audit for the gateway reload token."""

import datetime as dt
import hashlib
import sqlite3
import time
from pathlib import Path


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


class TokenStore:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure()

    def _connect(self):
        deadline = time.monotonic() + 30
        while True:
            connection = None
            try:
                connection = sqlite3.connect(self.db_path, timeout=30)
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA busy_timeout=30000")
                connection.execute("PRAGMA journal_mode=WAL")
                return connection
            except sqlite3.OperationalError as exc:
                if connection is not None:
                    connection.close()
                if "locked" in str(exc).lower() and time.monotonic() < deadline:
                    time.sleep(0.1)
                    continue
                raise
            except sqlite3.Error:
                if connection is not None:
                    connection.close()
                raise

    def _ensure(self):
        connection = self._connect()
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS gateway_token_meta (
                    id INTEGER PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    rotated_at TEXT NOT NULL,
                    last_used_at TEXT,
                    fingerprint_sha256 TEXT NOT NULL,
                    label TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS gateway_token_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    result TEXT NOT NULL,
                    details TEXT NOT NULL
                );
                """
            )
            connection.commit()
        finally:
            connection.close()

    def rotate(self, token, actor="api"):
        fingerprint = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = _now()
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    "INSERT INTO gateway_token_meta"
                    " (id, created_at, rotated_at, last_used_at, fingerprint_sha256, label)"
                    " VALUES (1, ?, ?, NULL, ?, '')"
                    " ON CONFLICT(id) DO UPDATE SET"
                    " rotated_at=excluded.rotated_at,"
                    " fingerprint_sha256=excluded.fingerprint_sha256",
                    (now, now, fingerprint),
                )
                connection.execute(
                    "INSERT INTO gateway_token_audit"
                    " (created_at, actor, action, result, details) VALUES (?, ?, ?, ?, ?)",
                    (now, str(actor), "rotate", "ok", "{}"),
                )
        finally:
            connection.close()
        return fingerprint

    def revoke(self, actor="api"):
        now = _now()
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    "UPDATE gateway_token_meta SET rotated_at=?, fingerprint_sha256='' WHERE id=1",
                    (now,),
                )
                connection.execute(
                    "INSERT INTO gateway_token_audit"
                    " (created_at, actor, action, result, details) VALUES (?, ?, ?, ?, ?)",
                    (now, str(actor), "revoke", "ok", "{}"),
                )
        finally:
            connection.close()

    def mark_used(self, actor="api", action="use"):
        now = _now()
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    "UPDATE gateway_token_meta SET last_used_at=? WHERE id=1", (now,)
                )
                connection.execute(
                    "INSERT INTO gateway_token_audit"
                    " (created_at, actor, action, result, details) VALUES (?, ?, ?, ?, ?)",
                    (now, str(actor), str(action), "ok", "{}"),
                )
        finally:
            connection.close()

    def metadata(self):
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM gateway_token_meta WHERE id=1"
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return {}
        return {
            "created_at": row["created_at"],
            "rotated_at": row["rotated_at"],
            "last_used_at": row["last_used_at"],
            "fingerprint_sha256": row["fingerprint_sha256"],
            "label": row["label"],
        }

    def audit(self, limit=100):
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM gateway_token_audit ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        finally:
            connection.close()
        return [
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "actor": row["actor"],
                "action": row["action"],
                "result": row["result"],
                "details": row["details"],
            }
            for row in rows
        ]
