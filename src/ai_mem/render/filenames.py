"""Deterministic note filenames.

Pattern: "<YYYY-MM-DD> - <slug>.md" where the date is the chat's created_at
in UTC and the slug is derived from the title. Collisions get a short hash
suffix so two chats with the same day + title still produce distinct paths.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from slugify import slugify

from ai_mem.schema import NormalizedChat
from ai_mem.util.hashing import short_id

MAX_SLUG_LEN = 60


def chat_slug(title: str) -> str:
    s = slugify(title or "untitled", max_length=MAX_SLUG_LEN, word_boundary=True)
    return s or "untitled"


def note_filename(chat: NormalizedChat, *, collision_tag: str | None = None) -> str:
    date = chat.created_at.astimezone().strftime("%Y-%m-%d")
    slug = chat_slug(chat.title)
    if collision_tag:
        return f"{date} - {slug} - {collision_tag}.md"
    return f"{date} - {slug}.md"


def note_relpath(chat: NormalizedChat, notes_subdir: str) -> Path:
    """Relative path inside the vault: <notes_subdir>/<platform>/YYYY-MM/<file>."""
    month = chat.created_at.astimezone().strftime("%Y-%m")
    return Path(notes_subdir) / chat.platform / month / note_filename(chat)


def attachment_filename(
    sha256: str, original_filename: str | None, mime_type: str | None = None
) -> str:
    prefix = short_id(sha256)
    if original_filename:
        safe = slugify(
            Path(original_filename).stem, max_length=40, word_boundary=True
        ) or "file"
        ext = Path(original_filename).suffix.lower() or _ext_from_mime(mime_type)
        return f"{prefix}-{safe}{ext}"
    return f"{prefix}{_ext_from_mime(mime_type)}"


def attachment_relpath(chat_id: str, filename: str, notes_subdir: str) -> Path:
    return Path(notes_subdir) / "attachments" / chat_id / filename


_MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "application/json": ".json",
}


def _ext_from_mime(mime: str | None) -> str:
    if not mime:
        return ""
    return _MIME_TO_EXT.get(mime.lower(), "")


def _day_stamp(dt: datetime) -> str:
    return dt.astimezone().strftime("%Y-%m-%d")
