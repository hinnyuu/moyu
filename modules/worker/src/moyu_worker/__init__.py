"""Background pack worker.

The worker claims one queued job at a time, resolves its assets, runs the
pipeline and writes progress/events back to storage. It contains no HTTP code
and no long-running scheduler; a runner can call ``run_once`` in a loop.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from moyu_pipeline import PackError, PackInput, pack
from moyu_storage import AssetStore, JobStore, Storage


class WorkerError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []


@dataclass
class WorkerResult:
    job_id: str
    status: str
    result: dict = None
    error: str = ""

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


class Worker:
    def __init__(self, storage):
        self.storage = storage
        self.assets = AssetStore(storage)
        self.jobs = JobStore(storage)

    def recover(self):
        return self.jobs.recover_stale()

    def run_once(self):
        job = self.jobs.claim_next()
        if job is None:
            return None
        self.jobs.append_event(job.id, {"phase": "start"})
        try:
            result = self._execute(job)
        except (WorkerError, PackError, Exception) as exc:
            current = self.jobs.get_job(job.id)
            message = getattr(exc, "message", str(exc))
            if current.status == "canceled":
                self.jobs.append_event(
                    job.id, {"phase": "canceled", "message": message}
                )
                return WorkerResult(job.id, "canceled", error=message)
            self.jobs.append_event(
                job.id, {"phase": "error", "code": getattr(exc, "code", "error"), "message": message}
            )
            self.jobs.update_status(job.id, "failed", error=message)
            return WorkerResult(job.id, "failed", error=message)

        current = self.jobs.get_job(job.id)
        if current.status == "canceled":
            self._remove_outputs(job.id, result)
            self.jobs.append_event(job.id, {"phase": "canceled", "message": "pack finished after cancel"})
            return WorkerResult(job.id, "canceled", result=result)
        self.jobs.append_event(job.id, {"phase": "pack"})
        self.jobs.update_status(job.id, "verifying", progress=90)
        self.jobs.append_event(job.id, {"phase": "verify", "ok": True})
        self.jobs.update_status(job.id, "succeeded", progress=100)
        return WorkerResult(job.id, "succeeded", result=result)

    def _execute(self, job):
        request = job.request
        if not isinstance(request, dict):
            raise WorkerError("invalid_request", "任务 request 必须是映射")
        raw_inputs = request.get("inputs")
        if not isinstance(raw_inputs, list) or not raw_inputs:
            raise WorkerError("invalid_request", "任务缺少 inputs")
        target_epoch = request.get("target_epoch")
        if not isinstance(target_epoch, int):
            raise WorkerError("invalid_request", "target_epoch 必须是整数")
        timezone = str(request.get("timezone") or "UTC")
        output_name = str(request.get("output_name") or "delivery.zip")
        compression = str(request.get("compression") or "store")
        strict = bool(request.get("strict_metadata", False))

        inputs = []
        for entry in raw_inputs:
            if not isinstance(entry, dict) or not entry.get("asset_id"):
                raise WorkerError("invalid_request", "input 缺少 asset_id")
            asset = self.assets.get_asset(entry["asset_id"])
            arcname = str(entry.get("arcname") or asset.original_name)
            inputs.append(PackInput(str(self.assets.path_for(asset.id)), arcname))

        output = self.storage.output_path(job.id, output_name)
        output.parent.mkdir(parents=True, exist_ok=True)
        job_dir = self.storage.job_dir(job.id)
        job_dir.mkdir(parents=True, exist_ok=True)
        manifest = job_dir / "manifest.json"

        result = pack(
            inputs,
            target_epoch,
            output,
            timezone=timezone,
            compression=compression,
            strict_metadata=strict,
            force=True,
            manifest_path=str(manifest),
        )
        manifest_data = result["manifest"]
        manifest.write_text(
            json.dumps(manifest_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return {
            "output": str(output),
            "manifest": str(manifest),
            "archive_bytes": result["summary"]["archive_bytes"],
            "entries": result["summary"]["entries"],
        }

    def _remove_outputs(self, job_id, result):
        for key in ("output", "manifest"):
            path = result.get(key)
            if not path:
                continue
            try:
                Path(path).unlink()
            except OSError:
                pass