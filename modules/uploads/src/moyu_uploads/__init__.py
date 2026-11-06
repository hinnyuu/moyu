"""tus-style upload sessions backed by the storage module.

A session owns ``uploads/<id>/data`` plus ``meta.json``. Offsets are updated in
``state.db`` through :class:`moyu_storage.Storage`. Chunks must arrive in order;
the store never trusts a client-provided path.
"""

import datetime as dt
import json
import os
import uuid
from dataclasses import dataclass

from moyu_storage import AssetStore, StorageError

DEFAULT_MEDIA_TYPE = "application/octet-stream"
STATUS_OPEN = "open"
STATUS_FINISHED = "finished"
STATUS_CANCELED = "canceled"


class UploadError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []

    def to_dict(self):
        return {"code": self.code, "message": self.message, "details": self.details}


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _new_id():
    return uuid.uuid4().hex


@dataclass
class UploadSession:
    id: str
    filename: str
    size: int
    offset: int
    status: str
    media_type: str
    created_at: str
    updated_at: str


class UploadSessionStore:
    def __init__(self, storage, max_upload_bytes, session_ttl_seconds=86400):
        self.storage = storage
        self.max_upload_bytes = int(max_upload_bytes)
        self.session_ttl_seconds = int(session_ttl_seconds)
        self.storage.ensure_layout()

    def _meta_path(self, session_id):
        return self.storage.upload_path(session_id).parent / "meta.json"

    def _write_meta(self, session_id, metadata):
        path = self._meta_path(session_id)
        fd, tmp = __import__("tempfile").mkstemp(
            prefix=".moyu-upload-", suffix=".part", dir=path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(metadata, handle, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
            tmp = None
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    def _read_meta(self, session_id):
        path = self._meta_path(session_id)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _row(self, session_id):
        with self.storage.connect() as conn:
            row = conn.execute(
                "SELECT * FROM upload_sessions WHERE id=?", (str(session_id),)
            ).fetchone()
        if row is None:
            raise UploadError("session_not_found", f"上传会话不存在: {session_id}")
        return row

    def _session(self, row):
        meta = self._read_meta(row["id"])
        return UploadSession(
            id=row["id"],
            filename=row["filename"],
            size=row["size"],
            offset=row["offset"],
            status=row["status"],
            media_type=meta.get("media_type", DEFAULT_MEDIA_TYPE),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create_session(self, metadata):
        filename = str(metadata.get("filename") or "upload.bin")
        try:
            size = int(metadata.get("size"))
        except (TypeError, ValueError) as exc:
            raise UploadError("invalid_size", "上传大小必须是整数") from exc
        if size < 0:
            raise UploadError("invalid_size", "上传大小不能为负")
        if size > self.max_upload_bytes:
            raise UploadError(
                "upload_too_large",
                "文件超过上传上限",
                [f"size={size}", f"max={self.max_upload_bytes}"],
            )
        self.storage.check_quota(size)
        media_type = str(metadata.get("media_type") or DEFAULT_MEDIA_TYPE)

        session_id = _new_id()
        data_path = self.storage.upload_path(session_id)
        try:
            data_path.parent.mkdir(parents=True, exist_ok=True)
            data_path.touch()
        except OSError as exc:
            raise UploadError("session_write_failed", f"无法创建上传文件: {exc}") from exc
        self._write_meta(
            session_id,
            {
                "filename": filename,
                "media_type": media_type,
                "size": size,
            },
        )
        now = _now()
        with self.storage.connect() as conn:
            conn.execute(
                "INSERT INTO upload_sessions"
                " (id, filename, size, offset, status, created_at, updated_at)"
                " VALUES (?, ?, ?, 0, ?, ?, ?)",
                (session_id, filename, size, STATUS_OPEN, now, now),
            )
        return self.get_session(session_id)

    def get_session(self, session_id):
        return self._session(self._row(session_id))

    def get_offset(self, session_id):
        return self._row(session_id)["offset"]

    def append_chunk(self, session_id, offset, data):
        row = self._row(session_id)
        if row["status"] != STATUS_OPEN:
            raise UploadError("session_closed", f"上传会话已关闭: {session_id}")
        if not isinstance(offset, int) or offset < 0:
            raise UploadError("invalid_offset", "偏移量必须是非负整数")
        if offset != row["offset"]:
            raise UploadError(
                "offset_mismatch",
                "偏移量与服务器不一致",
                [f"expected={row['offset']}", f"got={offset}"],
            )
        if not data:
            return row["offset"]
        end = offset + len(data)
        if end > row["size"]:
            raise UploadError(
                "chunk_too_large",
                "分片超过声明的文件大小",
                [f"end={end}", f"size={row['size']}"],
            )
        self.storage.check_quota(len(data))
        path = self.storage.upload_path(session_id)
        try:
            with open(path, "r+b") as handle:
                handle.seek(offset)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise UploadError("chunk_write_failed", f"写入分片失败: {exc}") from exc
        now = _now()
        with self.storage.connect() as conn:
            conn.execute(
                "UPDATE upload_sessions SET offset=?, updated_at=? WHERE id=?",
                (end, now, session_id),
            )
        return end

    def finish_session(self, session_id):
        session = self.get_session(session_id)
        if session.status != STATUS_OPEN:
            raise UploadError("session_closed", f"上传会话已关闭: {session_id}")
        if session.offset != session.size:
            raise UploadError(
                "upload_incomplete",
                "上传尚未完成",
                [f"offset={session.offset}", f"size={session.size}"],
            )
        path = self.storage.upload_path(session_id)
        try:
            asset = AssetStore(self.storage).register_asset(
                path,
                original_name=session.filename,
                media_type=session.media_type,
            )
        except StorageError as exc:
            raise UploadError(exc.code, exc.message, exc.details) from exc
        self._remove_session(session_id)
        return asset

    def cancel_session(self, session_id):
        self._row(session_id)
        self._remove_session(session_id)
        return True

    def _remove_session(self, session_id):
        directory = self.storage.upload_path(session_id).parent
        try:
            if directory.exists():
                import shutil

                shutil.rmtree(directory, ignore_errors=True)
        except OSError:
            pass
        with self.storage.connect() as conn:
            conn.execute("DELETE FROM upload_sessions WHERE id=?", (str(session_id),))

    def expire_sessions(self, ttl_seconds=None):
        ttl = self.session_ttl_seconds if ttl_seconds is None else int(ttl_seconds)
        removed = self.storage.cleanup(upload_ttl_seconds=ttl)
        return removed["uploads"]