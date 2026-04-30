"""Tests for render/note.py and render/transcript.py."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from ai_mem.parse.claude import ClaudeParser
from ai_mem.render import note
from ai_mem.render.frontmatter import FRONTMATTER_KEYS

FIXTURES = Path(__file__).parent / "fixtures" / "claude"
FIXED_IMPORT = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def _load(fixture_name: str, tmp_path: Path):
    src = FIXTURES / fixture_name
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    (export_dir / "conversations.json").write_bytes(src.read_bytes())
    parser = ClaudeParser()
    return list(parser.parse(export_dir))[0]


# ---------------------------------------------------------------------------
# 1. Deterministic render — same input → byte-identical output
# ---------------------------------------------------------------------------


def test_deterministic_render(tmp_path):
    chat = _load("conversations-simple.json", tmp_path)
    rn1 = note.render(chat, imported_at=FIXED_IMPORT)
    rn2 = note.render(chat, imported_at=FIXED_IMPORT)
    assert rn1.markdown == rn2.markdown


# ---------------------------------------------------------------------------
# 2. imported_at override appears in note
# ---------------------------------------------------------------------------


def test_imported_at_override(tmp_path):
    chat = _load("conversations-simple.json", tmp_path)
    fixed = datetime(2025, 6, 1, 0, 0, tzinfo=UTC)
    rn = note.render(chat, imported_at=fixed)
    assert "2025-06-01" in rn.markdown


# ---------------------------------------------------------------------------
# 3. Markdown structure — sections present in all fixtures
# ---------------------------------------------------------------------------


def test_markdown_structure_simple(tmp_path):
    chat = _load("conversations-simple.json", tmp_path)
    rn = note.render(chat, imported_at=FIXED_IMPORT)
    md = rn.markdown
    assert f"# {chat.title}" in md
    assert "## Sources & artifacts" in md
    assert "## Conversation" in md
    assert md.startswith("---\n")


def test_markdown_structure_attachment(tmp_path):
    chat = _load("conversations-attachment.json", tmp_path)
    rn = note.render(chat, imported_at=FIXED_IMPORT)
    md = rn.markdown
    assert f"# {chat.title}" in md
    assert "## Sources & artifacts" in md
    assert "## Conversation" in md
    assert md.startswith("---\n")


def test_markdown_structure_tool_citations(tmp_path):
    chat = _load("conversations-tool-citations.json", tmp_path)
    rn = note.render(chat, imported_at=FIXED_IMPORT)
    md = rn.markdown
    assert f"# {chat.title}" in md
    assert "## Sources & artifacts" in md
    assert "## Conversation" in md
    assert md.startswith("---\n")


# ---------------------------------------------------------------------------
# 4. Role emojis present in transcript
# ---------------------------------------------------------------------------


def test_role_emojis(tmp_path):
    chat = _load("conversations-simple.json", tmp_path)
    rn = note.render(chat, imported_at=FIXED_IMPORT)
    assert "👤 User" in rn.markdown
    assert "🤖 Assistant" in rn.markdown


# ---------------------------------------------------------------------------
# 5. Thinking block collapsed in details
# ---------------------------------------------------------------------------


def test_thinking_collapsed(tmp_path):
    chat = _load("conversations-tool-citations.json", tmp_path)
    rn = note.render(chat, imported_at=FIXED_IMPORT)
    assert "<details>" in rn.markdown
    assert "<summary>Thinking</summary>" in rn.markdown


# ---------------------------------------------------------------------------
# 6. Tool call and tool result markers
# ---------------------------------------------------------------------------


def test_tool_blocks(tmp_path):
    chat = _load("conversations-tool-citations.json", tmp_path)
    rn = note.render(chat, imported_at=FIXED_IMPORT)
    assert "**Tool call:**" in rn.markdown
    assert "**Tool result:**" in rn.markdown


# ---------------------------------------------------------------------------
# 7. Citation footnotes in tool-citations fixture
# ---------------------------------------------------------------------------


def test_citation_footnotes(tmp_path):
    chat = _load("conversations-tool-citations.json", tmp_path)
    rn = note.render(chat, imported_at=FIXED_IMPORT)
    # There should be at least one footnote reference [^c-...]
    assert "[^c-" in rn.markdown
    # And at least one footnote definition line starting with [^c-
    definition_lines = [ln for ln in rn.markdown.splitlines() if ln.startswith("[^c-")]
    assert len(definition_lines) >= 1


# ---------------------------------------------------------------------------
# 8. Uploaded section — attachment fixture has link, simple has _None._
# ---------------------------------------------------------------------------


def test_uploaded_section_with_attachment(tmp_path):
    chat = _load("conversations-attachment.json", tmp_path)
    rn = note.render(chat, imported_at=FIXED_IMPORT)
    # Should contain the attachment filename linked
    assert "sample-0.txt" in rn.markdown
    assert "### Uploaded by me" in rn.markdown


def test_uploaded_section_none_for_simple(tmp_path):
    chat = _load("conversations-simple.json", tmp_path)
    rn = note.render(chat, imported_at=FIXED_IMPORT)
    assert "_None._" in rn.markdown


# ---------------------------------------------------------------------------
# 9. Attachment stub — attachment fixture produces one stub
# ---------------------------------------------------------------------------


def test_attachment_stub(tmp_path):
    chat = _load("conversations-attachment.json", tmp_path)
    rn = note.render(chat, imported_at=FIXED_IMPORT)

    assert len(rn.attachment_stubs) == 1
    stub = rn.attachment_stubs[0]
    assert stub.vault_rel_path.suffix == ".md"
    assert "## Extracted content" in stub.markdown
    assert "sample-0.txt" in stub.markdown


# ---------------------------------------------------------------------------
# 10. Stable frontmatter key order
# ---------------------------------------------------------------------------


def test_frontmatter_key_order(tmp_path):
    chat = _load("conversations-simple.json", tmp_path)
    rn = note.render(chat, imported_at=FIXED_IMPORT)

    # Extract the frontmatter block between the first two ---
    lines = rn.markdown.splitlines()
    assert lines[0] == "---"
    end_idx = lines.index("---", 1)
    fm_text = "\n".join(lines[1:end_idx])
    data = yaml.safe_load(fm_text)
    keys_in_doc = list(data)

    # Keys that are present should appear in FRONTMATTER_KEYS order
    expected_order = [k for k in FRONTMATTER_KEYS if k in data]
    assert keys_in_doc == expected_order
