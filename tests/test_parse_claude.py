"""Tests for ClaudeParser. Written first (TDD); run against stub to confirm failures,
then against the real implementation to confirm passing."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from ai_mem.parse.claude import ClaudeParser

FIXTURES = Path(__file__).parent / "fixtures" / "claude"


def _write_export(tmp_path: Path, fixture_name: str) -> Path:
    """Copy a fixture into a temp export_dir as 'conversations.json'."""
    src = FIXTURES / fixture_name
    dst = tmp_path / "conversations.json"
    dst.write_bytes(src.read_bytes())
    return tmp_path


# ---------------------------------------------------------------------------
# 1. Happy path per fixture
# ---------------------------------------------------------------------------


def test_simple_fixture_basic(tmp_path):
    export_dir = _write_export(tmp_path, "conversations-simple.json")
    parser = ClaudeParser()
    chats = list(parser.parse(export_dir))

    assert len(chats) == 1
    chat = chats[0]
    assert chat.id == "d1ccc65d-9f38-4f3f-a28e-eeba0bf8e4ad"
    assert chat.title == "Fixture — simple text"
    assert len(chat.messages) == 2
    assert chat.platform == "claude"
    assert chat.has_alternate_branches is False


def test_attachment_fixture_basic(tmp_path):
    export_dir = _write_export(tmp_path, "conversations-attachment.json")
    parser = ClaudeParser()
    chats = list(parser.parse(export_dir))

    assert len(chats) == 1
    chat = chats[0]
    assert chat.id == "1e2e978f-53b7-4fe4-a7fc-39cfa11e1776"
    assert chat.title == "Fixture — attachment with extracted content"
    assert len(chat.messages) == 2
    assert chat.platform == "claude"
    assert chat.has_alternate_branches is False


def test_tool_citations_fixture_basic(tmp_path):
    export_dir = _write_export(tmp_path, "conversations-tool-citations.json")
    parser = ClaudeParser()
    chats = list(parser.parse(export_dir))

    assert len(chats) == 1
    chat = chats[0]
    assert chat.id == "a1211ff5-7347-4909-abe8-a946e1070552"
    assert chat.title == "Fixture — tool_use + citations"
    assert len(chat.messages) == 2
    assert chat.platform == "claude"
    assert chat.has_alternate_branches is False


# ---------------------------------------------------------------------------
# 2. Role mapping
# ---------------------------------------------------------------------------


def test_role_mapping(tmp_path):
    export_dir = _write_export(tmp_path, "conversations-simple.json")
    parser = ClaudeParser()
    chat = list(parser.parse(export_dir))[0]

    assert chat.messages[0].role == "user"
    assert chat.messages[1].role == "assistant"


# ---------------------------------------------------------------------------
# 3. Thinking blocks
# ---------------------------------------------------------------------------


def test_thinking_blocks_present(tmp_path):
    export_dir = _write_export(tmp_path, "conversations-tool-citations.json")
    parser = ClaudeParser()
    chat = list(parser.parse(export_dir))[0]

    thinking_blocks = [
        blk
        for msg in chat.messages
        for blk in msg.content
        if blk.kind == "thinking"
    ]
    assert len(thinking_blocks) >= 1


# ---------------------------------------------------------------------------
# 4. Tool blocks
# ---------------------------------------------------------------------------


def test_tool_call_and_result_blocks(tmp_path):
    export_dir = _write_export(tmp_path, "conversations-tool-citations.json")
    parser = ClaudeParser()
    chat = list(parser.parse(export_dir))[0]

    all_blocks = [blk for msg in chat.messages for blk in msg.content]
    kinds = {blk.kind for blk in all_blocks}
    assert "tool_call" in kinds
    assert "tool_result" in kinds


# ---------------------------------------------------------------------------
# 5. Citations / web_sources
# ---------------------------------------------------------------------------


def test_citations_deduped(tmp_path):
    export_dir = _write_export(tmp_path, "conversations-tool-citations.json")
    parser = ClaudeParser()
    chat = list(parser.parse(export_dir))[0]

    # 4 citations in the fixture, all same URL -> deduped to 1
    assert len(chat.web_sources) == 1
    for ws in chat.web_sources:
        # id should be hex string of length 12
        assert len(ws.id) == 12
        assert all(c in "0123456789abcdef" for c in ws.id)


# ---------------------------------------------------------------------------
# 6. Attachment extraction
# ---------------------------------------------------------------------------


def test_attachment_extraction(tmp_path):
    export_dir = _write_export(tmp_path, "conversations-attachment.json")
    parser = ClaudeParser()
    chat = list(parser.parse(export_dir))[0]

    assert len(chat.attachments) >= 1

    # Find the txt attachment
    txt_att = next(
        (a for a in chat.attachments if a.original_filename == "sample-0.txt"), None
    )
    assert txt_att is not None
    assert txt_att.mime_type == "text/plain"
    assert txt_att.extracted_content is not None
    assert len(txt_att.extracted_content) > 0


# ---------------------------------------------------------------------------
# 7. Deterministic IDs
# ---------------------------------------------------------------------------


def test_deterministic_ids(tmp_path):
    export_dir = _write_export(tmp_path, "conversations-attachment.json")
    parser = ClaudeParser()

    chat1 = list(parser.parse(export_dir))[0]
    chat2 = list(parser.parse(export_dir))[0]

    assert chat1.id == chat2.id
    ids1 = sorted(a.id for a in chat1.attachments)
    ids2 = sorted(a.id for a in chat2.attachments)
    assert ids1 == ids2


# ---------------------------------------------------------------------------
# 8. Per-chat failure isolation
# ---------------------------------------------------------------------------


def test_per_chat_failure_isolation(tmp_path, caplog):
    bad_conv = [
        {
            "uuid": "bad-uuid-0000",
            "name": "Bad chat",
            "summary": "",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "account": {"uuid": "00000000-0000-4000-8000-aaaaaaaaaaaa"},
            # Missing chat_messages intentionally — will cause parse error
        },
        {
            "uuid": "good-uuid-1111",
            "name": "Good chat",
            "summary": "",
            "created_at": "2024-01-02T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "account": {"uuid": "00000000-0000-4000-8000-aaaaaaaaaaaa"},
            "chat_messages": [
                {
                    "uuid": "msg-uuid-aaaa",
                    "text": "hello",
                    "content": [{"type": "text", "text": "hello", "citations": []}],
                    "sender": "human",
                    "created_at": "2024-01-02T00:00:00Z",
                    "updated_at": "2024-01-02T00:00:00Z",
                    "attachments": [],
                    "files": [],
                    "parent_message_uuid": "00000000-0000-4000-8000-000000000000",
                }
            ],
        },
    ]
    export_dir = tmp_path
    (export_dir / "conversations.json").write_text(json.dumps(bad_conv))

    parser = ClaudeParser()
    with caplog.at_level(logging.WARNING, logger="ai_mem.parse.claude"):
        chats = list(parser.parse(export_dir))

    # Should yield the good chat
    assert len(chats) == 1
    assert chats[0].id == "good-uuid-1111"

    # Should have logged a warning about the bad one
    assert any("bad-uuid-0000" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# 9. Missing conversations.json
# ---------------------------------------------------------------------------


def test_missing_conversations_json(tmp_path):
    parser = ClaudeParser()
    with pytest.raises((FileNotFoundError, Exception)):
        list(parser.parse(tmp_path))


# ---------------------------------------------------------------------------
# 10. Unknown content block type — must not crash
# ---------------------------------------------------------------------------


def test_unknown_block_type_skipped(tmp_path, caplog):
    conv = [
        {
            "uuid": "unknown-block-uuid",
            "name": "Unknown block chat",
            "summary": "",
            "created_at": "2024-01-03T00:00:00Z",
            "updated_at": "2024-01-03T00:00:00Z",
            "account": {"uuid": "00000000-0000-4000-8000-aaaaaaaaaaaa"},
            "chat_messages": [
                {
                    "uuid": "msg-uuid-bbbb",
                    "text": "hello",
                    "content": [
                        {"type": "text", "text": "normal text", "citations": []},
                        {"type": "future_unknown", "data": "some future data"},
                    ],
                    "sender": "assistant",
                    "created_at": "2024-01-03T00:00:00Z",
                    "updated_at": "2024-01-03T00:00:00Z",
                    "attachments": [],
                    "files": [],
                    "parent_message_uuid": "00000000-0000-4000-8000-000000000000",
                }
            ],
        }
    ]
    export_dir = tmp_path
    (export_dir / "conversations.json").write_text(json.dumps(conv))

    parser = ClaudeParser()
    with caplog.at_level(logging.WARNING, logger="ai_mem.parse.claude"):
        chats = list(parser.parse(export_dir))

    assert len(chats) == 1
    chat = chats[0]
    # The known text block should still be there
    all_blocks = [blk for msg in chat.messages for blk in msg.content]
    assert any(blk.kind == "text" for blk in all_blocks)


# ---------------------------------------------------------------------------
# Additional: URL and branch_count
# ---------------------------------------------------------------------------


def test_url_and_branch_count(tmp_path):
    export_dir = _write_export(tmp_path, "conversations-simple.json")
    parser = ClaudeParser()
    chat = list(parser.parse(export_dir))[0]

    assert chat.url == "https://claude.ai/chat/d1ccc65d-9f38-4f3f-a28e-eeba0bf8e4ad"
    assert chat.branch_count == 1
    assert chat.model is None
