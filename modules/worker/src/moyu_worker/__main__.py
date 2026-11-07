"""Container entrypoint for the worker role."""

import os
import signal
import threading

from moyu_config import ConfigProvider
from moyu_storage import Storage

from . import Worker


def required(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"缺少环境变量 {name}")
    return value


def main():
    provider = ConfigProvider(required("MOYU_CONFIG_DIR"))
    effective = provider.load()
    storage_config = effective.modules["storage"]
    storage = Storage(
        storage_config["dataRoot"],
        quota_bytes=storage_config.get("quotaBytes", 0),
    ).ensure_layout()
    worker = Worker(storage)

    stop = threading.Event()

    def handler(_signum, _frame):
        stop.set()

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)

    requeued = worker.recover()
    if requeued:
        print(f"moyu-worker: requeued {requeued} interrupted jobs", flush=True)

    poll = int(effective.modules["worker"].get("pollIntervalSeconds", 2))
    while not stop.is_set():
        result = worker.run_once()
        if result is None:
            stop.wait(poll)
        else:
            print(
                f"moyu-worker: job {result.job_id} {result.status}",
                flush=True,
            )
    print("moyu-worker: stopped", flush=True)


if __name__ == "__main__":
    main()