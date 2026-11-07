"""ffmpeg / OpenImageIO based video and EXR helpers."""

import json
import shutil
import subprocess
from pathlib import Path


class ExternalError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []


def ffmpeg_available():
    return bool(shutil.which("ffmpeg"))


def ffprobe_available():
    return bool(shutil.which("ffprobe"))


def oiiotool_available():
    return bool(shutil.which("oiiotool"))


def probe_video(path, timeout=20):
    if not ffprobe_available():
        return {"supported": False, "reason": "ffprobe 不可用", "type": "video"}
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExternalError("probe_failed", f"ffprobe 失败: {exc}") from exc
    if completed.returncode != 0:
        raise ExternalError(
            "probe_failed",
            "ffprobe 无法读取视频",
            [completed.stderr.decode("utf-8", "replace")[-500:]],
        )
    try:
        data = json.loads(completed.stdout.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ExternalError("probe_failed", "ffprobe 输出非 JSON") from exc
    stream = next(
        (item for item in data.get("streams", []) if item.get("codec_type") == "video"),
        None,
    )
    if stream is None:
        return {"supported": False, "reason": "没有视频流", "type": "video"}
    duration = data.get("format", {}).get("duration")
    return {
        "type": "video",
        "supported": ffmpeg_available(),
        "format": stream.get("codec_name", "unknown"),
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "duration": float(duration) if duration else None,
        "frames": None,
        "reason": None if ffmpeg_available() else "ffmpeg 不可用",
    }


def generate_video(path, target, profile, timeout=60):
    if not ffmpeg_available():
        raise ExternalError("preview_unsupported", "ffmpeg 不可用")
    width = profile["maxWidth"]
    height = profile["maxHeight"]
    fmt = profile["format"]
    if fmt == "mp4":
        quality = profile.get("quality", 23)
        command = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(path),
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=decrease",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            str(quality),
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(target),
        ]
    else:
        command = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            "0",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=decrease",
            str(target),
        ]
    try:
        completed = subprocess.run(
            command, capture_output=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExternalError("preview_timeout", f"ffmpeg 超时或失败: {exc}") from exc
    if completed.returncode != 0:
        raise ExternalError(
            "preview_failed",
            "ffmpeg 生成预览失败",
            [completed.stderr.decode("utf-8", "replace")[-500:]],
        )
    return target


def probe_exr(path, timeout=20):
    if not oiiotool_available():
        return {"supported": False, "reason": "oiiotool 不可用", "type": "image"}
    return {
        "type": "image",
        "supported": True,
        "format": "exr",
        "width": None,
        "height": None,
        "frames": 1,
        "reason": None,
    }


def generate_exr(path, target, profile, timeout=60):
    if not oiiotool_available():
        raise ExternalError("preview_unsupported", "oiiotool 不可用")
    width = profile["maxWidth"]
    height = profile["maxHeight"]
    command = [
        "oiiotool",
        str(path),
        "--resize",
        f"{width}x{height}",
        "-o",
        str(target),
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExternalError("preview_timeout", f"oiiotool 超时或失败: {exc}") from exc
    if completed.returncode != 0:
        raise ExternalError(
            "preview_failed",
            "oiiotool 生成预览失败",
            [completed.stderr.decode("utf-8", "replace")[-500:]],
        )
    return target
