"""Hashing helpers. Canonical JSON hash is used as the chat content_hash
that drives idempotency. Must be stable across runs and Python versions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def canonical_json_hash(obj: Any) -> str:
    """Stable sha256 of a JSON-serializable object.

    Sorted keys, no whitespace, default str for datetimes/paths so hashes
    don't shift when pydantic upgrades change repr.
    """
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def short_id(full_hash: str, length: int = 12) -> str:
    return full_hash[:length]
