#!/usr/bin/env python3
"""Verify a single entry larger than 4 GiB (ZIP64)."""

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "modules" / "archive-zip" / "src"))

from moyu_archive_zip import ArchiveWriter, verify_archive  # noqa: E402

DOS = (2026, 1, 2, 3, 4, 4)
SIZE = 4 * 1024**3 + 1024  # just over 4 GiB


def main():
    work = Path(tempfile.mkdtemp(prefix="moyu-large-"))
    try:
        free = shutil.disk_usage(work).free
        if free < SIZE + 3 * 1024**3:
            raise SystemExit(f"磁盘不足：free={free}")

        source = work / "large.bin"
        with open(source, "wb") as handle:
            handle.truncate(SIZE)
        output = work / "large.zip"

        started = time.monotonic()
        writer = ArchiveWriter(output, verify=False)
        writer.add_file("large.bin", DOS, source)
        summary = writer.finalize()

        result = verify_archive(output, {"large.bin": {"dos": DOS}})
        assert result["ok"], result["problems"]
        assert output.stat().st_size > SIZE
        assert summary.total_bytes == SIZE

        with open(output, "rb") as handle:
            handle.seek(0)
            head = handle.read(4)
        assert head == b"PK\x03\x04"

        print("PASS")
        print(f"size={SIZE} archive={output.stat().st_size} elapsed={time.monotonic() - started:.1f}s")
        print(f"compression={summary.compression} verified={summary.verified}")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
