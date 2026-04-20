"""Snapshot tests for the render stage.

Run with --snapshot-update to create or refresh snapshots.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ai_mem.parse.claude import ClaudeParser
from ai_mem.render import note

FIXTURES = Path(__file__).parent / "fixtures" / "claude"
FIXED_IMPORT = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def _load(fixture_name: str, tmp_path: Path):
    src = FIXTURES / fixture_name
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    (export_dir / "conversations.json").write_bytes(src.read_bytes())
    parser = ClaudeParser()
    return list(parser.parse(export_dir))[0]


def test_snapshot_simple_note(snapshot, tmp_path):
    chat = _load("conversations-simple.json", tmp_path)
    rn = note.render(chat, imported_at=FIXED_IMPORT)
    snapshot.assert_match(rn.markdown, "claude_simple_note.md")


def test_snapshot_attachment_note(snapshot, tmp_path):
    chat = _load("conversations-attachment.json", tmp_path)
    rn = note.render(chat, imported_at=FIXED_IMPORT)
    snapshot.assert_match(rn.markdown, "claude_attachment_note.md")


def test_snapshot_tool_citations_note(snapshot, tmp_path):
    chat = _load("conversations-tool-citations.json", tmp_path)
    rn = note.render(chat, imported_at=FIXED_IMPORT)
    snapshot.assert_match(rn.markdown, "claude_tool_citations_note.md")


def test_snapshot_attachment_stub(snapshot, tmp_path):
    chat = _load("conversations-attachment.json", tmp_path)
    rn = note.render(chat, imported_at=FIXED_IMPORT)
    assert len(rn.attachment_stubs) >= 1
    stub = rn.attachment_stubs[0]
    snapshot.assert_match(stub.markdown, "claude_attachment_stub.md")
