"""Tests for fetch.archive.extract: happy path and ZipSlip rejection."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from ai_mem.fetch.archive import extract


def _make_zip(tmp_path: Path, entries: dict[str, str]) -> Path:
    """Create a ZIP file with the given {name: content} entries."""
    zip_path = tmp_path / "test.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    zip_path.write_bytes(buf.getvalue())
    return zip_path


def test_extract_happy_path(tmp_path):
    zip_path = _make_zip(
        tmp_path,
        {
            "conversations.json": '[{"uuid": "abc"}]',
            "subdir/file.txt": "hello",
        },
    )
    dest = tmp_path / "out"
    result = extract(zip_path, dest)

    assert result == dest
    assert dest.is_dir()
    assert (dest / "conversations.json").exists()
    assert (dest / "subdir" / "file.txt").read_text() == "hello"


def test_extract_creates_dest(tmp_path):
    zip_path = _make_zip(tmp_path, {"a.txt": "content"})
    dest = tmp_path / "nested" / "dest"
    assert not dest.exists()

    extract(zip_path, dest)

    assert dest.is_dir()
    assert (dest / "a.txt").exists()


def test_zipslip_dotdot_rejected(tmp_path):
    zip_path = _make_zip(tmp_path, {"../evil.md": "evil"})
    dest = tmp_path / "dest"

    with pytest.raises(ValueError, match="ZipSlip"):
        extract(zip_path, dest)


def test_zipslip_absolute_path_rejected(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("/etc/passwd")
        zf.writestr(info, "root:x:0:0")
    zip_path = tmp_path / "malicious.zip"
    zip_path.write_bytes(buf.getvalue())
    dest = tmp_path / "dest"

    with pytest.raises(ValueError, match="ZipSlip"):
        extract(zip_path, dest)


def test_zipslip_nested_dotdot_rejected(tmp_path):
    zip_path = _make_zip(tmp_path, {"subdir/../../evil.txt": "evil"})
    dest = tmp_path / "dest"

    with pytest.raises(ValueError, match="ZipSlip"):
        extract(zip_path, dest)
