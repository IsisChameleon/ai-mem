"""Copy downloaded ZIPs into ~/ai-archive/raw/<platform>/ and extract to a temp dir
for parsing. Keeps the original ZIP untouched for forensics/reprocessing.
"""

from __future__ import annotations

from pathlib import Path


def archive(zip_path: Path, platform: str, raw_archive_root: Path) -> Path:
    """Move or copy zip_path into raw_archive_root/<platform>/. Stub."""
    raise NotImplementedError("fetch.archive.archive pending")


def extract(zip_path: Path, dest: Path) -> Path:
    """Extract ZIP safely to dest. Rejects absolute paths / .. traversal. Stub."""
    raise NotImplementedError("fetch.archive.extract pending")
