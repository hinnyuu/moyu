"""Media metadata adapters.

``core`` contains the format implementations. ``adapters`` provides a thin
registry so callers can discover an adapter by format name or by file header.
"""

from . import core
from .adapters import ADAPTERS, Adapter, adapter_by_name, adapter_for
from .core import (
    BytesReader,
    FileReader,
    MetadataError,
    MetadataInfo,
    Patch,
    apply_patches,
    avif_items,
    build_metadata_patches,
    detect_format,
    iter_patched_chunks,
    materialize_metadata,
    patch_to_dict,
)

__all__ = [
    "ADAPTERS",
    "Adapter",
    "BytesReader",
    "FileReader",
    "MetadataError",
    "MetadataInfo",
    "Patch",
    "adapter_by_name",
    "adapter_for",
    "apply_patches",
    "avif_items",
    "build_metadata_patches",
    "detect_format",
    "iter_patched_chunks",
    "materialize_metadata",
    "patch_to_dict",
]