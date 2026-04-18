from datetime import datetime, timezone

from ai_mem.render.filenames import (
    attachment_filename,
    attachment_relpath,
    chat_slug,
    note_filename,
    note_relpath,
)
from ai_mem.schema import NormalizedChat


def _chat(title: str = "Hello, world!") -> NormalizedChat:
    dt = datetime(2025, 11, 7, 15, 30, tzinfo=timezone.utc)
    return NormalizedChat(
        id="abc123",
        platform="claude",
        title=title,
        created_at=dt,
        updated_at=dt,
    )


def test_slug_lowercases_and_strips_punctuation() -> None:
    assert chat_slug("Hello, World!") == "hello-world"
    assert chat_slug("") == "untitled"
    assert chat_slug("   ") == "untitled"


def test_note_filename_is_deterministic() -> None:
    c = _chat()
    a = note_filename(c)
    b = note_filename(c)
    assert a == b
    assert a.endswith(".md")
    assert a.startswith("2025-11-07")


def test_note_filename_collision_tag_changes_name() -> None:
    c = _chat()
    assert note_filename(c) != note_filename(c, collision_tag="dup01")


def test_note_relpath_has_platform_and_month() -> None:
    c = _chat()
    p = note_relpath(c, notes_subdir="AI Chats")
    parts = p.parts
    assert parts[0] == "AI Chats"
    assert parts[1] == "claude"
    assert parts[2] == "2025-11"
    assert parts[3].endswith(".md")


def test_attachment_filename_uses_short_hash() -> None:
    sha = "a" * 64
    name = attachment_filename(sha, "Report FINAL v2.pdf", "application/pdf")
    assert name.startswith("aaaaaaaaaaaa-")
    assert name.endswith(".pdf")


def test_attachment_filename_falls_back_to_mime() -> None:
    sha = "b" * 64
    name = attachment_filename(sha, None, "image/png")
    assert name == "bbbbbbbbbbbb.png"


def test_attachment_relpath_structure() -> None:
    p = attachment_relpath("chat-abc", "xyz-file.pdf", "AI Chats")
    assert p.parts == ("AI Chats", "attachments", "chat-abc", "xyz-file.pdf")
