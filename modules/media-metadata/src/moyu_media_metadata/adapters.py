"""Adapter registry for media metadata formats.

Each adapter exposes ``detect``, ``inspect``/``plan`` and ``apply``. The heavy
lifting lives in :mod:`moyu_media_metadata.core`; adapters only declare how a
format is recognised and which implementation to call.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from . import core


def _exr(header: bytes) -> bool:
    return header[:4] == b"v/1\x01"


def _png(header: bytes) -> bool:
    return header.startswith(core.PNG_SIG)


def _jpeg(header: bytes) -> bool:
    return header[:2] == b"\xff\xd8"


def _tiff(header: bytes) -> bool:
    return header[:4] in (b"II*\x00", b"MM\x00*")


def _webp(header: bytes) -> bool:
    return header[:4] == b"RIFF" and header[8:12] == b"WEBP"


def _mkv(header: bytes) -> bool:
    return header[:4] == b"\x1a\x45\xdf\xa3"


def _ftyp(header: bytes) -> bool:
    return header[4:8] == b"ftyp"


@dataclass(frozen=True)
class Adapter:
    format: str
    detect_fn: Callable[[bytes], bool]
    suffixes: tuple
    notes: str = ""

    def detect(self, header: bytes) -> bool:
        return self.detect_fn(header)

    def inspect(self, path, target_epoch, tz) -> core.MetadataInfo:
        info = core.build_metadata_patches(path, target_epoch, tz)
        if info.format not in (self.format, "unknown"):
            raise core.MetadataError(
                f"{path}: 期望 {self.format}，实际识别为 {info.format}"
            )
        return info

    def plan(self, path, target_epoch, tz) -> core.MetadataInfo:
        return self.inspect(path, target_epoch, tz)

    def apply(self, data: bytes, plan: core.MetadataInfo) -> bytes:
        return core.apply_patches(data, plan.patches)

    def stream(self, path, plan: core.MetadataInfo, chunk_size=1024 * 1024):
        return core.iter_patched_chunks(path, plan.patches, chunk_size)

    def materialize(self, path, plan, target_epoch, tz, dest_dir):
        return core.materialize_metadata(path, plan, target_epoch, tz, dest_dir)


ADAPTERS = {
    "exr": Adapter("exr", _exr, (".exr",), "OpenEXR 头字段"),
    "png": Adapter("png", _png, (".png",), "tEXt/eXIf/zTXt/iTXt，压缩字段需要 materialize"),
    "jpeg": Adapter("jpeg", _jpeg, (".jpg", ".jpeg"), "COM/EXIF/XMP/APP13"),
    "tiff": Adapter("tiff", _tiff, (".tif", ".tiff"), "EXIF/XMP/Photoshop IRB"),
    "webp": Adapter("webp", _webp, (".webp",), "EXIF/XMP"),
    "avif": Adapter("avif", _ftyp, (".avif",), "Exif/XMP，依赖 iinf/iloc"),
    "mp4": Adapter("mp4", _ftyp, (".mp4",), "mvhd/tkhd/mdhd 与 ©day"),
    "mov": Adapter("mov", _ftyp, (".mov",), "QuickTime 容器"),
    "mkv": Adapter("mkv", _mkv, (".mkv", ".webm"), "DATE/DateUTC"),
}


def adapter_by_name(name: str) -> Optional[Adapter]:
    return ADAPTERS.get(name)


def adapter_for(path) -> Optional[Adapter]:
    name = core.detect_format(path)
    if name is None:
        return None
    return ADAPTERS.get(name)