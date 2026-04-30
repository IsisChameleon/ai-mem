"""Tests for the ingest pipeline (src/ai_mem/pipeline.py)."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_mem.config import LLM, Attachments, Config, Gmail, Logging, Paths
from ai_mem.pipeline import ingest

FIXTURES = Path(__file__).parent / "fixtures" / "claude"

SIMPLE_CHAT_ID = "d1ccc65d-9f38-4f3f-a28e-eeba0bf8e4ad"
ATTACHMENT_CHAT_ID = "1e2e978f-53b7-4fe4-a7fc-39cfa11e1776"


def _make_config(tmp_path: Path) -> Config:
    """Construct a minimal Config pointing all paths into tmp_path."""
    vault = tmp_path / "vault"
    vault.mkdir()
    return Config(
        paths=Paths(
            vault=vault,
            notes_subdir="AI Chats",
            raw_archive=tmp_path / "raw",
            failed=tmp_path / "failed",
            sync_state=tmp_path / "sync-state.json",
        ),
        attachments=Attachments(),
        gmail=Gmail(
            credentials=tmp_path / "credentials.json",
            token=tmp_path / "token.json",
            scope="https://www.googleapis.com/auth/gmail.readonly",
            query="",
        ),
        llm=LLM(
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
            api_key_env="ANTHROPIC_API_KEY",
        ),
        logging=Logging(),
    )


def _write_export(tmp_path: Path, fixture_name: str) -> Path:
    """Copy a fixture JSON to a temp directory as conversations.json."""
    export_dir = tmp_path / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    src = FIXTURES / fixture_name
    (export_dir / "conversations.json").write_bytes(src.read_bytes())
    return export_dir


def _write_multi_export(tmp_path: Path, fixture_names: list[str]) -> Path:
    """Merge multiple fixture JSON arrays into one conversations.json."""
    export_dir = tmp_path / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    all_chats = []
    for name in fixture_names:
        all_chats.extend(json.loads((FIXTURES / name).read_bytes()))
    (export_dir / "conversations.json").write_text(
        json.dumps(all_chats), encoding="utf-8"
    )
    return export_dir


# ---------------------------------------------------------------------------
# 1. End-to-end on simple fixture
# ---------------------------------------------------------------------------


def test_simple_end_to_end(tmp_path):
    cfg = _make_config(tmp_path)
    export_dir = _write_export(tmp_path, "conversations-simple.json")

    result = ingest(export_dir, cfg)

    assert result.chats_seen == 1
    assert result.chats_written == 1
    assert result.chats_skipped == 0
    assert result.chats_failed == 0

    # Note written at expected path.
    note_path = cfg.paths.vault / "AI Chats" / "claude" / "2024-07" / "2024-07-09 - fixture-simple-text.md"
    assert note_path.exists(), f"Expected note at {note_path}"
    assert len(result.notes_paths) == 1
    assert result.notes_paths[0] == note_path

    # State file has one entry with non-empty hashes.
    assert cfg.paths.sync_state.exists()
    state_data = json.loads(cfg.paths.sync_state.read_text())
    chats = state_data["chats"]
    assert len(chats) == 1
    key = f"claude:{SIMPLE_CHAT_ID}"
    assert key in chats
    entry = chats[key]
    assert entry["content_hash"]
    assert entry["note_path"]


# ---------------------------------------------------------------------------
# 2. Attachment fixture writes stub
# ---------------------------------------------------------------------------


def test_attachment_stub_written(tmp_path):
    cfg = _make_config(tmp_path)
    export_dir = _write_export(tmp_path, "conversations-attachment.json")

    result = ingest(export_dir, cfg)

    assert result.chats_written == 1
    assert result.stubs_written >= 1

    # Stub lives under AI Chats/attachments/<chat-id>/
    attachments_dir = cfg.paths.vault / "AI Chats" / "attachments" / ATTACHMENT_CHAT_ID
    stub_files = list(attachments_dir.glob("*.md"))
    assert len(stub_files) >= 1

    stub_content = stub_files[0].read_text()
    assert "## Extracted content" in stub_content


# ---------------------------------------------------------------------------
# 3. Idempotency — second run skips unchanged chat
# ---------------------------------------------------------------------------


def test_idempotency(tmp_path):
    cfg = _make_config(tmp_path)
    export_dir = _write_export(tmp_path, "conversations-simple.json")

    result1 = ingest(export_dir, cfg)
    assert result1.chats_written == 1

    note_path = result1.notes_paths[0]
    mtime_before = note_path.stat().st_mtime_ns

    result2 = ingest(export_dir, cfg)

    assert result2.chats_written == 0
    assert result2.chats_skipped == 1

    mtime_after = note_path.stat().st_mtime_ns
    assert mtime_before == mtime_after, "Note mtime changed on second run (should not be rewritten)"


# ---------------------------------------------------------------------------
# 4. Content change triggers rewrite
# ---------------------------------------------------------------------------


def test_content_change_triggers_rewrite(tmp_path):
    cfg = _make_config(tmp_path)
    export_dir = _write_export(tmp_path, "conversations-simple.json")

    result1 = ingest(export_dir, cfg)
    assert result1.chats_written == 1

    # Modify the conversation name in the fixture copy.
    conv_path = export_dir / "conversations.json"
    data = json.loads(conv_path.read_text())
    data[0]["name"] = "Modified Title For Test"
    conv_path.write_text(json.dumps(data), encoding="utf-8")

    result2 = ingest(export_dir, cfg)

    assert result2.chats_written == 1

    # Find the new note (slug will differ) and confirm updated title.
    note_files = list((cfg.paths.vault / "AI Chats" / "claude" / "2024-07").glob("*.md"))
    assert any("Modified Title For Test" in f.read_text() for f in note_files)


# ---------------------------------------------------------------------------
# 5. Dry-run writes nothing
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing(tmp_path):
    cfg = _make_config(tmp_path)
    export_dir = _write_export(tmp_path, "conversations-simple.json")

    result = ingest(export_dir, cfg, dry_run=True)

    assert result.chats_written == 1

    # Vault should be empty (no notes written).
    note_files = list(cfg.paths.vault.rglob("*.md"))
    assert note_files == [], f"Dry-run wrote files: {note_files}"

    # State file should not exist.
    assert not cfg.paths.sync_state.exists()


# ---------------------------------------------------------------------------
# 6. only_chat_id filter
# ---------------------------------------------------------------------------


def test_only_chat_id_filter(tmp_path):
    cfg = _make_config(tmp_path)
    # Two chats: simple + attachment.
    export_dir = _write_multi_export(
        tmp_path, ["conversations-simple.json", "conversations-attachment.json"]
    )

    result = ingest(export_dir, cfg, only_chat_id=SIMPLE_CHAT_ID)

    # Only the simple chat note should exist.
    assert result.chats_written == 1
    # Filter out attachment stubs — just check notes under claude/
    claude_notes = list((cfg.paths.vault / "AI Chats" / "claude").glob("**/*.md"))
    assert len(claude_notes) == 1

    # Attachment chat note should NOT exist.
    att_notes = list((cfg.paths.vault / "AI Chats" / "claude").glob(f"**/*{ATTACHMENT_CHAT_ID}*"))
    assert att_notes == []

    # The filtered-out chat should be counted.
    assert result.chats_filtered > 0


# ---------------------------------------------------------------------------
# 7. since filter
# ---------------------------------------------------------------------------


def test_since_filter(tmp_path):
    cfg = _make_config(tmp_path)
    export_dir = _write_multi_export(
        tmp_path, ["conversations-simple.json", "conversations-attachment.json"]
    )

    # Both chats are from 2024-07; set since to after both.
    future = datetime(2030, 1, 1, tzinfo=UTC)
    result = ingest(export_dir, cfg, since=future)

    assert result.chats_written == 0
    assert result.chats_skipped == 2
    # No notes written.
    notes = list(cfg.paths.vault.rglob("*.md"))
    assert notes == []


# ---------------------------------------------------------------------------
# 8. Per-chat failure isolation
# ---------------------------------------------------------------------------


def test_per_chat_failure_isolation(tmp_path):
    """Verify that a render failure on one chat doesn't abort the whole ingest.

    We patch render_note to raise for a specific chat ID so that the failure
    occurs inside the pipeline's per-chat try/except (the parser itself has
    its own isolation layer that swallows parser-level failures silently).
    """
    from unittest.mock import patch

    cfg = _make_config(tmp_path)
    # Two-chat export: simple + attachment.
    export_dir = _write_multi_export(
        tmp_path, ["conversations-simple.json", "conversations-attachment.json"]
    )

    # Patch render_note to raise for the attachment chat, which has the
    # attachment chat id; the simple chat should still be written.
    import ai_mem.render.note as _render_module
    _original_render = _render_module.render

    def _patched_render(chat, **kw):
        if chat.id == ATTACHMENT_CHAT_ID:
            raise RuntimeError("Simulated render failure for test")
        return _original_render(chat, **kw)

    with patch("ai_mem.pipeline.render_note", side_effect=_patched_render):
        result = ingest(export_dir, cfg)

    # Simple chat should be written successfully.
    assert result.chats_written == 1
    # Attachment chat should be counted as failed.
    assert result.chats_failed == 1

    # Failure dump file should exist.
    dump_file = cfg.paths.failed / f"claude-{ATTACHMENT_CHAT_ID}.json"
    assert dump_file.exists(), f"Expected failure dump at {dump_file}"

    # Good chat note should exist.
    good_notes = list((cfg.paths.vault / "AI Chats" / "claude").glob("**/*.md"))
    assert len(good_notes) >= 1


# ---------------------------------------------------------------------------
# 9. ZIP ingest
# ---------------------------------------------------------------------------


def test_zip_ingest(tmp_path):
    cfg = _make_config(tmp_path)

    # Build a ZIP from the simple fixture.
    zip_path = tmp_path / "export.zip"
    fixture_data = (FIXTURES / "conversations-simple.json").read_bytes()
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("conversations.json", fixture_data)

    result = ingest(zip_path, cfg)

    assert result.chats_written == 1
    note_path = cfg.paths.vault / "AI Chats" / "claude" / "2024-07" / "2024-07-09 - fixture-simple-text.md"
    assert note_path.exists()


# ---------------------------------------------------------------------------
# 10. Temp directory is cleaned up even when ZipSlip raises (Critical #1)
# ---------------------------------------------------------------------------


def test_tempdir_cleaned_on_zipslip(tmp_path, monkeypatch):
    """Verify that TemporaryDirectory.cleanup() is called even when extract() raises."""
    cfg = _make_config(tmp_path)

    zip_path = tmp_path / "malicious.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.md", "evil content")
    zip_path.write_bytes(buf.getvalue())

    cleanup_called = []
    original_cleanup = __import__("tempfile").TemporaryDirectory.cleanup

    def _tracking_cleanup(self):
        cleanup_called.append(True)
        original_cleanup(self)

    monkeypatch.setattr(
        __import__("tempfile").TemporaryDirectory, "cleanup", _tracking_cleanup
    )

    with pytest.raises(ValueError, match="ZipSlip"):
        ingest(zip_path, cfg)

    assert cleanup_called, "TemporaryDirectory.cleanup() was not called after ZipSlip exception"
