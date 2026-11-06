import datetime as dt
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "modules" / "storage" / "src"))

from moyu_storage import (  # noqa: E402
    AssetStore,
    JobStore,
    Storage,
    StorageError,
)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "data"
        self.storage = Storage(self.data)
        self.storage.ensure_layout()

    def tearDown(self):
        self.tmp.cleanup()

    def test_layout_and_path_safety(self):
        for name in ("uploads", "assets", "jobs", "outputs", "preview"):
            self.assertTrue((self.data / name).is_dir())
        self.assertTrue((self.data / "state.db").exists())

        with self.assertRaises(StorageError) as ctx:
            self.storage.asset_path("../../etc/passwd")
        self.assertEqual(ctx.exception.code, "path_escape")
        with self.assertRaises(StorageError) as ctx:
            self.storage.upload_path("../../etc")
        self.assertEqual(ctx.exception.code, "path_escape")
        self.assertEqual(self.storage.output_path("job1", "../out.zip").name, "out.zip")
        with self.assertRaises(StorageError):
            self.storage.preview_path("asset1", "..")

    def test_asset_lifecycle(self):
        store = AssetStore(self.storage)
        source = Path(self.tmp.name) / "frame.exr"
        source.write_bytes(b"payload-123")
        asset = store.register_asset(source, original_name="frame.exr", media_type="image/exr")

        self.assertFalse(source.exists())
        self.assertEqual(asset.size, 11)
        self.assertEqual(asset.original_name, "frame.exr")
        self.assertTrue(Path(asset.path).exists())
        with store.open_asset(asset.id) as handle:
            self.assertEqual(handle.read(), b"payload-123")
        self.assertEqual(store.get_asset(asset.id).sha256, asset.sha256)
        self.assertEqual([item.id for item in store.list_assets()], [asset.id])

        store.delete_asset(asset.id)
        with self.assertRaises(StorageError) as ctx:
            store.get_asset(asset.id)
        self.assertEqual(ctx.exception.code, "asset_not_found")

    def test_quota_rejects_without_moving_source(self):
        storage = Storage(self.data, quota_bytes=8)
        store = AssetStore(storage)
        source = Path(self.tmp.name) / "big.bin"
        source.write_bytes(b"x" * 16)
        with self.assertRaises(StorageError) as ctx:
            store.register_asset(source)
        self.assertEqual(ctx.exception.code, "quota_exceeded")
        self.assertTrue(source.exists())

    def test_job_state_machine_and_events(self):
        jobs = JobStore(self.storage)
        job = jobs.create_job({"inputs": ["a"], "output": "out.zip"})
        self.assertEqual(job.status, "created")
        job = jobs.update_status(job.id, "queued")
        job = jobs.update_status(job.id, "running", progress=10)
        jobs.append_event(job.id, {"phase": "scan", "done": 1})
        job = jobs.update_status(job.id, "verifying", progress=90)
        job = jobs.update_status(job.id, "succeeded", progress=95)
        self.assertEqual(job.status, "succeeded")
        self.assertEqual(job.progress, 100)
        self.assertEqual(len(jobs.events(job.id)), 1)
        self.assertEqual(jobs.get_job(job.id).request["output"], "out.zip")

        bad = jobs.create_job({})
        with self.assertRaises(StorageError) as ctx:
            jobs.update_status(bad.id, "succeeded")
        self.assertEqual(ctx.exception.code, "job_transition_invalid")

    def test_cancel_and_terminal_state(self):
        jobs = JobStore(self.storage)
        job = jobs.create_job({})
        job = jobs.update_status(job.id, "queued")
        job = jobs.update_status(job.id, "running")
        canceled = jobs.cancel_job(job.id)
        self.assertEqual(canceled.status, "canceled")
        self.assertEqual(jobs.cancel_job(job.id).status, "canceled")

        done = jobs.create_job({})
        jobs.update_status(done.id, "queued")
        jobs.update_status(done.id, "running")
        jobs.update_status(done.id, "verifying")
        jobs.update_status(done.id, "succeeded")
        with self.assertRaises(StorageError) as ctx:
            jobs.update_status(done.id, "running")
        self.assertEqual(ctx.exception.code, "job_transition_invalid")

    def test_persistence_across_instances(self):
        store = AssetStore(self.storage)
        source = Path(self.tmp.name) / "a.bin"
        source.write_bytes(b"abc")
        asset = store.register_asset(source)
        jobs = JobStore(self.storage)
        jobs.create_job({"x": 1})

        again = Storage(self.data)
        again.ensure_layout()
        self.assertEqual(AssetStore(again).get_asset(asset.id).size, 3)
        self.assertEqual(len(JobStore(again).list_jobs()), 1)

    def test_cleanup_uploads_and_previews(self):
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)).isoformat()
        session_dir = self.data / "uploads" / "old"
        session_dir.mkdir(parents=True)
        (session_dir / "data").write_bytes(b"x")
        with self.storage.connect() as conn:
            conn.execute(
                "INSERT INTO upload_sessions (id, filename, size, offset, status, created_at, updated_at)"
                " VALUES ('old', 'a.bin', 1, 1, 'open', ?, ?)",
                (old, old),
            )
        preview = self.data / "preview" / "asset" / "thumb"
        preview.mkdir(parents=True)
        (preview / "x.jpg").write_bytes(b"p")
        past = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)).timestamp()
        os.utime(preview, (past, past))

        removed = self.storage.cleanup(upload_ttl_seconds=3600, preview_ttl_seconds=3600)
        self.assertEqual(removed, {"uploads": 1, "previews": 1})
        self.assertFalse(session_dir.exists())
        self.assertFalse(preview.exists())


if __name__ == "__main__":
    unittest.main()