"""Copy downloaded ZIPs into ~/ai-archive/raw/<platform>/ and extract to a temp dir
for parsing. Keeps the original ZIP untouched for forensics/reprocessing.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

log = logging.getLogger(__name__)


def archive(zip_path: Path, platform: str, raw_archive_root: Path) -> Path:
    """Move or copy zip_path into raw_archive_root/<platform>/. Stub."""
    raise NotImplementedError("fetch.archive.archive pending")


def extract(zip_path: Path, dest: Path) -> Path:
    """Extract ZIP safely to dest. Rejects absolute paths / .. traversal (ZipSlip guard).

    Args:
        zip_path: Path to the ZIP file to extract.
        dest: Destination directory to extract into.

    Returns:
        dest (the extraction directory).

    Raises:
        ValueError: If any ZIP entry has an absolute path or contains '..' traversal.
    """
    dest.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        for name in names:
            if name.startswith("/"):
                raise ValueError(f"ZipSlip: absolute path in ZIP entry: {name!r}")
            if ".." in Path(name).parts:
                raise ValueError(f"ZipSlip: '..' traversal in ZIP entry: {name!r}")
        zf.extractall(dest)

    log.info("extracted %d files to %s", len(names), dest)
    return dest
