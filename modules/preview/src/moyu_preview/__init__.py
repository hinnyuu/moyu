"""Image preview provider backed by Pillow.

Only raster images supported by Pillow are decoded in this minimal provider.
Video, EXR and other formats report ``supported: false`` until ffmpeg /
OpenImageIO providers are added. Cache keys include the asset sha256 and the
normalized profile, so identical assets share nothing across profiles.
"""

import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from moyu_storage import AssetStore, StorageError

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover - exercised by the CLI environment
    Image = None
    ImageOps = None

DEFAULT_PROFILES = {
    "thumb": {"maxWidth": 256, "maxHeight": 256, "format": "webp", "quality": 80},
    "view": {"maxWidth": 1920, "maxHeight": 1920, "format": "jpeg", "quality": 85},
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".avif", ".bmp", ".gif"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm"}
EXR_SUFFIXES = {".exr"}


class PreviewError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []

    def to_dict(self):
        return {"code": self.code, "message": self.message, "details": self.details}


@dataclass
class PreviewArtifact:
    asset_id: str
    profile: str
    path: str
    width: int
    height: int
    format: str
    bytes: int
    cached: bool

    def to_dict(self):
        return {
            "asset_id": self.asset_id,
            "profile": self.profile,
            "path": self.path,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "bytes": self.bytes,
            "cached": self.cached,
        }


def _normalize_profile(profile):
    if not isinstance(profile, dict):
        raise PreviewError("profile_invalid", "预览 profile 必须是映射")
    try:
        width = int(profile["maxWidth"])
        height = int(profile["maxHeight"])
        quality = int(profile.get("quality", 85))
    except (KeyError, TypeError, ValueError) as exc:
        raise PreviewError("profile_invalid", "profile 缺少 maxWidth/maxHeight") from exc
    fmt = str(profile.get("format", "webp")).lower()
    if width <= 0 or height <= 0:
        raise PreviewError("profile_invalid", "预览尺寸必须为正")
    if not 1 <= quality <= 100:
        raise PreviewError("profile_invalid", "quality 必须在 1-100")
    if fmt not in ("jpeg", "png", "webp"):
        raise PreviewError("profile_invalid", f"不支持的预览格式: {fmt}")
    return {
        "maxWidth": width,
        "maxHeight": height,
        "format": fmt,
        "quality": quality,
    }


class PreviewProvider:
    def __init__(
        self,
        storage,
        cache_dir=None,
        profiles=None,
        concurrency=2,
        max_memory_bytes=256 * 1024 * 1024,
        timeout_seconds=60,
    ):
        self.storage = storage
        self.assets = AssetStore(storage)
        self.cache_dir = Path(cache_dir) if cache_dir else storage.preview_dir
        self.profiles = dict(DEFAULT_PROFILES)
        if profiles:
            for name, profile in profiles.items():
                self.profiles[name] = _normalize_profile(profile)
        self.max_memory_bytes = int(max_memory_bytes)
        self.timeout_seconds = int(timeout_seconds)
        self._semaphore = threading.BoundedSemaphore(max(1, int(concurrency)))

    def _asset(self, asset_id):
        try:
            return self.assets.get_asset(asset_id)
        except StorageError as exc:
            raise PreviewError(exc.code, exc.message, exc.details) from exc

    def probe(self, asset_id):
        asset = self._asset(asset_id)
        path = self.assets.path_for(asset.id)
        suffix = path.suffix.lower() or Path(asset.original_name).suffix.lower()
        base = {
            "asset_id": asset.id,
            "path": str(path),
            "media_type": asset.media_type,
            "size": asset.size,
        }
        if suffix in VIDEO_SUFFIXES:
            return {**base, "type": "video", "format": suffix.lstrip("."), "supported": False,
                    "reason": "ffmpeg provider 尚未启用"}
        if suffix in EXR_SUFFIXES:
            return {**base, "type": "image", "format": "exr", "supported": False,
                    "reason": "OpenImageIO provider 尚未启用"}
        if suffix not in IMAGE_SUFFIXES:
            return {**base, "type": "unknown", "format": suffix.lstrip("."), "supported": False,
                    "reason": "未支持的格式"}
        if Image is None:
            return {**base, "type": "image", "format": suffix.lstrip("."), "supported": False,
                    "reason": "Pillow 不可用"}
        try:
            with Image.open(path) as image:
                return {
                    **base,
                    "type": "image",
                    "format": (image.format or suffix.lstrip(".")).lower(),
                    "width": image.width,
                    "height": image.height,
                    "mode": image.mode,
                    "frames": getattr(image, "n_frames", 1),
                    "supported": True,
                }
        except Exception as exc:
            raise PreviewError("probe_failed", f"无法读取图像: {exc}") from exc

    def _resolve_profile(self, profile):
        if isinstance(profile, str):
            try:
                return profile, self.profiles[profile]
            except KeyError as exc:
                raise PreviewError("profile_unknown", f"未知预览 profile: {profile}") from exc
        normalized = _normalize_profile(profile)
        return "custom", normalized

    def _cache_key(self, asset, profile):
        payload = json.dumps(
            {"sha256": asset.sha256, "profile": profile},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def preview_path(self, asset_id, profile):
        name, normalized = self._resolve_profile(profile)
        asset = self._asset(asset_id)
        key = self._cache_key(asset, normalized)
        return self.cache_dir / asset.id / key / f"preview.{normalized['format']}"

    def generate(self, asset_id, profile):
        name, normalized = self._resolve_profile(profile)
        asset = self._asset(asset_id)
        info = self.probe(asset.id)
        if not info.get("supported"):
            raise PreviewError(
                "preview_unsupported",
                f"暂不支持该格式: {info.get('reason', info.get('format'))}",
            )
        if Image is None:
            raise PreviewError("preview_unavailable", "Pillow 不可用")
        estimated = info["width"] * info["height"] * 4
        if estimated > self.max_memory_bytes:
            raise PreviewError(
                "preview_too_large",
                "图像解码内存超过限制",
                [f"estimated={estimated}", f"max={self.max_memory_bytes}"],
            )

        target = self.preview_path(asset.id, normalized)
        if target.exists():
            with Image.open(target) as image:
                return PreviewArtifact(
                    asset_id=asset.id,
                    profile=name,
                    path=str(target),
                    width=image.width,
                    height=image.height,
                    format=normalized["format"],
                    bytes=target.stat().st_size,
                    cached=True,
                )

        if not self._semaphore.acquire(timeout=self.timeout_seconds):
            raise PreviewError("preview_busy", "预览队列已满")
        started = time.monotonic()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(self.assets.path_for(asset.id)) as image:
                if ImageOps is not None:
                    image = ImageOps.exif_transpose(image)
                image.thumbnail(
                    (normalized["maxWidth"], normalized["maxHeight"]), Image.LANCZOS
                )
                if normalized["format"] == "jpeg":
                    if image.mode in ("RGBA", "LA", "P"):
                        background = Image.new("RGB", image.size, (255, 255, 255))
                        converted = image.convert("RGBA")
                        background.paste(converted, mask=converted.split()[-1])
                        image = background
                    else:
                        image = image.convert("RGB")
                fd, tmp = tempfile.mkstemp(
                    prefix=".moyu-preview-", suffix=".part", dir=target.parent
                )
                os.close(fd)
                try:
                    image.save(tmp, format=normalized["format"].upper(), quality=normalized["quality"])
                    os.replace(tmp, target)
                    tmp = None
                finally:
                    if tmp and os.path.exists(tmp):
                        try:
                            os.unlink(tmp)
                        except OSError:
                            pass
                width, height = image.size
            if time.monotonic() - started > self.timeout_seconds:
                target.unlink(missing_ok=True)
                raise PreviewError("preview_timeout", "预览生成超时")
            return PreviewArtifact(
                asset_id=asset.id,
                profile=name,
                path=str(target),
                width=width,
                height=height,
                format=normalized["format"],
                bytes=target.stat().st_size,
                cached=False,
            )
        finally:
            self._semaphore.release()

    def delete(self, asset_id):
        asset = self._asset(asset_id)
        directory = self.cache_dir / asset.id
        if directory.exists():
            shutil.rmtree(directory, ignore_errors=True)
        return True