import json
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for relative in (
    "modules/worker/src",
    "modules/pipeline/src",
    "modules/core-time/python",
    "modules/media-metadata/src",
    "modules/archive-zip/src",
    "modules/storage/src",
):
    sys.path.insert(0, str(ROOT / relative))

from moyu_storage import AssetStore, JobStore, Storage  # noqa: E402
from moyu_worker import Worker  # noqa: E402


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.tmp.name) / "data").ensure_layout()
        self.assets = AssetStore(self.storage)
        self.jobs = JobStore(self.storage)
        self.worker = Worker(self.storage)
        self.target = int(time.time()) + 3600
        source = Path(self.tmp.name) / "frame.bin"
        source.write_bytes(b"frame-data")
        self.asset = self.assets.register_asset(source, original_name="frame.bin")

    def tearDown(self):
        self.tmp.cleanup()

    def make_job(self, request=None):
        if request is None:
            request = {
                "inputs": [{"asset_id": self.asset.id, "arcname": "frames/frame.bin"}],
                "target_epoch": self.target,
                "timezone": "UTC",
                "output_name": "delivery.zip",
            }
        job = self.jobs.create_job(request)
        return self.jobs.update_status(job.id, "queued")

    def test_successful_pack(self):
        job = self.make_job()
        result = self.worker.run_once()
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "succeeded")
        finished = self.jobs.get_job(job.id)
        self.assertEqual(finished.status, "succeeded")
        self.assertEqual(finished.progress, 100)

        output = self.storage.output_path(job.id, "delivery.zip")
        manifest = self.storage.job_dir(job.id) / "manifest.json"
        self.assertTrue(output.exists())
        self.assertTrue(manifest.exists())
        data = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(data["entries"][0]["arcname"], "frames/frame.bin")
        with zipfile.ZipFile(output) as zf:
            self.assertEqual(zf.namelist(), ["frames/frame.bin"])
        phases = [event["event"]["phase"] for event in self.jobs.events(job.id)]
        self.assertEqual(phases, ["start", "pack", "verify"])

    def test_invalid_request_fails(self):
        job = self.make_job({})
        result = self.worker.run_once()
        self.assertEqual(result.status, "failed")
        finished = self.jobs.get_job(job.id)
        self.assertEqual(finished.status, "failed")
        self.assertIn("inputs", finished.error)

    def test_missing_asset_fails(self):
        job = self.make_job(
            {
                "inputs": [{"asset_id": "nope", "arcname": "x.bin"}],
                "target_epoch": self.target,
            }
        )
        result = self.worker.run_once()
        self.assertEqual(result.status, "failed")
        self.assertEqual(self.jobs.get_job(job.id).status, "failed")

    def test_canceled_job_is_not_claimed(self):
        job = self.make_job()
        self.jobs.cancel_job(job.id)
        self.assertIsNone(self.worker.run_once())
        self.assertEqual(self.jobs.get_job(job.id).status, "canceled")

    def test_recover_stale_jobs(self):
        job = self.make_job()
        with self.storage.connect() as conn:
            conn.execute("UPDATE jobs SET status='running' WHERE id=?", (job.id,))
        self.assertEqual(self.worker.recover(), 1)
        self.assertEqual(self.jobs.get_job(job.id).status, "queued")
        self.assertEqual(self.jobs.get_job(job.id).error, "worker restarted; requeued")

    def test_no_queued_jobs(self):
        self.assertIsNone(self.worker.run_once())


if __name__ == "__main__":
    unittest.main()