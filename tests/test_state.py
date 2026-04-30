from pathlib import Path

from ai_mem.sync.state import (
    ChatStateEntry,
    EmailStateEntry,
    LastIngestRecord,
    SyncState,
    chat_key,
    load,
    save,
)


def test_roundtrip_empty(tmp_path: Path) -> None:
    p = tmp_path / ".sync-state.json"
    save(SyncState(), p)
    loaded = load(p)
    assert loaded.version == 1
    assert loaded.chats == {}
    assert loaded.processed_emails == {}


def test_roundtrip_with_entries(tmp_path: Path) -> None:
    p = tmp_path / ".sync-state.json"
    state = SyncState(
        chats={
            chat_key("claude", "c1"): ChatStateEntry(
                content_hash="h1",
                note_path="AI Chats/claude/2025-11/a.md",
                updated_at="2025-11-07T00:00:00Z",
                rendered_at="2025-11-07T00:00:01Z",
                attachment_ids=["aaa", "bbb"],
            ),
        },
        processed_emails={
            "msg1": EmailStateEntry(
                platform="claude",
                received_at="2025-11-07T00:00:00Z",
                zip_path="~/ai-archive/raw/claude/x.zip",
            ),
        },
    )
    save(state, p)
    loaded = load(p)
    assert loaded.chats["claude:c1"].content_hash == "h1"
    assert loaded.chats["claude:c1"].attachment_ids == ["aaa", "bbb"]
    assert loaded.processed_emails["msg1"].platform == "claude"


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    loaded = load(tmp_path / "does-not-exist.json")
    assert loaded == SyncState()


def test_save_is_atomic(tmp_path: Path) -> None:
    p = tmp_path / ".sync-state.json"
    save(SyncState(), p)
    # No leftover .tmp file
    assert not (tmp_path / ".sync-state.json.tmp").exists()


def test_last_ingest_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / ".sync-state.json"
    state = SyncState(
        last_ingest=LastIngestRecord(
            at="2026-04-30T18:45:00+00:00",
            source_name="claude-export.zip",
            account="me@example.com",
            chats_seen=34,
            chats_written=2,
            chats_skipped=32,
            max_chat_updated_at="2026-04-29T10:00:00+00:00",
        ),
    )
    save(state, p)
    loaded = load(p)
    assert loaded.last_ingest is not None
    assert loaded.last_ingest.source_name == "claude-export.zip"
    assert loaded.last_ingest.chats_written == 2
    assert loaded.last_ingest.max_chat_updated_at == "2026-04-29T10:00:00+00:00"


def test_load_missing_last_ingest_returns_none(tmp_path: Path) -> None:
    p = tmp_path / ".sync-state.json"
    save(SyncState(), p)
    loaded = load(p)
    assert loaded.last_ingest is None
