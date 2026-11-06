"""Delivery ZIP writer and verifier for moyu.

The module only owns ZIP structure: entry names, DOS timestamps, extra fields,
CRC and atomic replacement. It does not parse media files or compute time
policies; callers pass a DOS timestamp per entry.
"""

from .dos import decode_dos, encode_dos, validate_dos
from .errors import ArchiveError
from .verify import parse_extra, verify_archive
from .writer import ArchiveWriter, ArchiveSummary

__all__ = [
    "ArchiveError",
    "ArchiveSummary",
    "ArchiveWriter",
    "decode_dos",
    "encode_dos",
    "parse_extra",
    "validate_dos",
    "verify_archive",
]