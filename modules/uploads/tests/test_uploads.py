import datetime as dt
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for relative in ("modules/uploads/src", "modules/storage/src"):
    sys.path.insert(0, str(ROOT / relative))

from moyu_storage import AssetStore, Storage  # noqa: E402
from moyu_uploads import UploadError, UploadSessionStore  # noqa: E402


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.tmp.name) / "data")
        self.storage.ensure_layout()
        self.uploads = UploadSessionStore(
            self.storage, max_upload_bytes=1024, session_ttl_seconds=3600
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_upload_and_finish(self):
        session = self.uploads.create_session(
            {"filename": "frame.exr", "size": 10, "media_type": "image/exr"}
        )
        self.assertEqual(session.offset, 0)
        self.assertEqual(self.uploads.append_chunk(session.id, 0, b"0123"), 4)
        self.assertEqual(self.uploads.append_chunk(session.id, 4, b"456789"), 10)
        self.assertEqual(self.uploads.get_session(session.id).offset, 10)

        asset = self.uploads.finish_session(session.id)
        self.assertEqual(asset.size, 10)
        self.assertEqual(asset.original_name, "frame.exr")
        self.assertEqual(asset.media_type, "image/exr")
        self.assertEqual(asset.sha256, hashlib.sha256(b"0123456789").hexdigest())
        with AssetStore(self.storage).open_asset(asset.id) as handle:
            self.assertEqual(handle.read(), b"0123456789")
        with self.assertRaises(UploadError) as ctx:
            self.uploads.get_session(session.id)
        self.assertEqual(ctx.exception.code, "session_not_found")
        self.assertFalse((self.storage.uploads_dir / session.id).exists())

    def test_offset_and_size_validation(self):
        session = self.uploads.create_session({"filename": "a.bin", "size": 4})
        with self.assertRaises(UploadError) as ctx:
            self.uploads.append_chunk(session.id, 1, b"x")
        self.assertEqual(ctx.exception.code, "offset_mismatch")
        with self.assertRaises(UploadError) as ctx:
            self.uploads.append_chunk(session.id, 0, b"12345")
        self.assertEqual(ctx.exception.code, "chunk_too_large")
        with self.assertRaises(UploadError) as ctx:
            self.uploads.finish_session(session.id)
        self.assertEqual(ctx.exception.code, "upload_incomplete")

    def test_max_size_and_quota(self):
        with self.assertRaises(UploadError) as ctx:
            self.uploads.create_session({"filename": "big.bin", "size": 2048})
        self.assertEqual(ctx.exception.code, "upload_too_large")

        storage = Storage(Path(self.tmp.name) / "small", quota_bytes=8)
        storage.ensure_layout()
        uploads = UploadSessionStore(storage, max_upload_bytes=1024)
        with self.assertRaises(Exception) as ctx:
            uploads.create_session({"filename": "a.bin", "size": 16})
        self.assertEqual(ctx.exception.code, "quota_exceeded")

    def test_finished_session_cannot_append(self):
        session = self.uploads.create_session({"filename": "a.bin", "size": 3})
        self.uploads.append_chunk(session.id, 0, b"abc")
        self.uploads.finish_session(session.id)
        with self.assertRaises(UploadError) as ctx:
            self.uploads.append_chunk(session.id, 3, b"d")
        self.assertEqual(ctx.exception.code, "session_not_found")

    def test_cancel_and_expire(self):
        session = self.uploads.create_session({"filename": "a.bin", "size": 4})
        self.uploads.append_chunk(session.id, 0, b"ab")
        self.assertTrue(self.uploads.cancel_session(session.id))
        self.assertFalse((self.storage.uploads_dir / session.id).exists())

        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)).isoformat()
        stale = self.uploads.create_session({"filename": "b.bin", "size": 1})
        with self.storage.connect() as conn:
            conn.execute(
                "UPDATE upload_sessions SET updated_at=? WHERE id=?",
                (old, stale.id),
            )
        self.assertEqual(self.uploads.expire_sessions(ttl_seconds=60), 1)

    def test_persistence_across_instances(self):
        session = self.uploads.create_session({"filename": "a.bin", "size": 2})
        self.uploads.append_chunk(session.id, 0, b"a")

        other = UploadSessionStore(
            Storage(self.storage.data_root), max_upload_bytes=1024
        )
        self.assertEqual(other.get_offset(session.id), 1)
        self.assertEqual(other.append_chunk(session.id, 1, b"b"), 2)

    def test_invalid_size(self):
        with self.assertRaises(UploadError) as ctx:
            self.uploads.create_session({"filename": "a.bin", "size": "x"})
        self.assertEqual(ctx.exception.code, "invalid_size")
        with self.assertRaises(UploadError) as ctx:
            self.uploads.create_session({"filename": "a.bin", "size": -1})
        self.assertEqual(ctx.exception.code, "invalid_size")


if __name__ == "__main__":
    unittest.main()