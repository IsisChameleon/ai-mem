"""Assemble the full Markdown note for a NormalizedChat."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

from ai_mem.render import filenames, frontmatter, transcript
from ai_mem.schema import Attachment, NormalizedChat


@dataclass(frozen=True)
class RenderedAttachmentStub:
    vault_rel_path: Path
    markdown: str
    attachment: Attachment


@dataclass(frozen=True)
class RenderedNote:
    chat_id: str
    platform: str
    vault_rel_path: Path
    markdown: str
    attachments: list[Attachment]
    attachment_stubs: list[RenderedAttachmentStub] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PLATFORM_LABEL = {
    "claude": "Claude",
    "chatgpt": "ChatGPT",
}


def _platform_label(platform: str) -> str:
    return _PLATFORM_LABEL.get(platform, platform.capitalize())


def _human_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes // 1024} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _info_callout(chat: NormalizedChat, imported_at: datetime) -> str:
    platform = _platform_label(chat.platform)
    model = chat.model or "unknown model"
    c_date = chat.created_at.strftime("%Y-%m-%d")
    u_date = chat.updated_at.strftime("%Y-%m-%d")
    date_range = c_date if c_date == u_date else f"{c_date} through {u_date}"
    n = len(chat.messages)
    imp_date = imported_at.strftime("%Y-%m-%d")
    return f"> [!info] **{platform}** · {model} · {date_range} · {n} messages · imported {imp_date}"


def _uploaded_section(chat: NormalizedChat) -> str:
    uploads = [a for a in chat.attachments if a.kind == "user_upload"]
    if not uploads:
        return "_None._"
    lines = []
    for att in uploads:
        name = att.original_filename or att.id
        mime = att.mime_type or "unknown"
        size = _human_size(att.size_bytes)
        lines.append(f"- [[{att.vault_rel_path}|{name}]] — {mime}, {size}")
    return "\n".join(lines)


def _generated_section(chat: NormalizedChat) -> str:
    if not chat.artifacts:
        return "_None._"
    lines = []
    for art in chat.artifacts:
        lines.append(f"- [[|{art.title}]] — {art.kind}")
    return "\n".join(lines)


def _web_sources_section(chat: NormalizedChat) -> str:
    if not chat.web_sources:
        return "_None._"
    # Build a mapping from citation id -> first citing message short id
    cit_msg: dict[str, str] = {}
    for msg in chat.messages:
        for cid in msg.citation_ids:
            if cid not in cit_msg:
                cit_msg[cid] = msg.id[:8]

    lines = []
    for ws in chat.web_sources:
        label = ws.title or ws.url
        short_msg = cit_msg.get(ws.id, ws.cited_in_message_id[:8])
        lines.append(f"- [{label}]({ws.url}) — cited in message {short_msg}")
    return "\n".join(lines)


def _sources_section(chat: NormalizedChat) -> str:
    return "\n\n".join([
        "## Sources & artifacts",
        "### Uploaded by me",
        _uploaded_section(chat),
        "### Generated during the conversation",
        _generated_section(chat),
        "### Web sources referenced",
        _web_sources_section(chat),
    ])


def _attachment_stub_markdown(att: Attachment, chat_id: str) -> str:
    """Build the stub note markdown for an attachment with extracted_content."""
    mime = att.mime_type or "unknown"
    size = _human_size(att.size_bytes)
    name = att.original_filename or att.id

    fm_data = {
        "id": att.id,
        "sha256": att.sha256,
        "original_filename": att.original_filename,
        "mime_type": mime,
        "size_bytes": att.size_bytes,
        "kind": att.kind,
        "chat_id": chat_id,
        "uploaded_at": att.uploaded_at.isoformat() if att.uploaded_at else None,
    }
    fm_yaml = yaml.safe_dump(
        fm_data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    fm_block = f"---\n{fm_yaml}---"

    lines = [
        fm_block,
        "",
        f"# {name}",
        "",
        f"> [!info] **Attachment extracted from Claude export** · {mime} · {size}",
        "",
        "## Extracted content",
        "",
        att.extracted_content or "",
    ]
    body = "\n".join(lines)
    # Ensure single trailing newline, strip trailing whitespace per line
    stripped_lines = [ln.rstrip() for ln in body.splitlines()]
    return "\n".join(stripped_lines).rstrip("\n") + "\n"


def _clean(markdown: str) -> str:
    """Strip trailing whitespace per line and ensure single trailing newline."""
    lines = [ln.rstrip() for ln in markdown.splitlines()]
    return "\n".join(lines).rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render(
    chat: NormalizedChat,
    notes_subdir: str = "AI Chats",
    imported_at: datetime | None = None,
) -> RenderedNote:
    """Render a NormalizedChat into a RenderedNote."""
    if imported_at is None:
        imported_at = datetime.now(UTC)

    vault_rel = filenames.note_relpath(chat, notes_subdir)

    fm_block = frontmatter.to_yaml_block(chat, imported_at)
    info = _info_callout(chat, imported_at)
    summary_body = chat.summary or "_(pending)_"
    sources = _sources_section(chat)
    conversation = transcript.render(chat)

    parts = [
        fm_block,
        f"# {chat.title}",
        info,
        "## Summary",
        summary_body,
        sources,
        conversation,
    ]
    raw_markdown = "\n\n".join(parts)
    markdown = _clean(raw_markdown)

    # Build attachment stubs
    stubs: list[RenderedAttachmentStub] = []
    for att in chat.attachments:
        if att.extracted_content is None:
            continue
        # Stub note lives at same vault_rel_path but with .md extension
        stub_path = att.vault_rel_path.with_suffix(".md")
        stub_md = _attachment_stub_markdown(att, chat.id)
        stubs.append(RenderedAttachmentStub(
            vault_rel_path=stub_path,
            markdown=stub_md,
            attachment=att,
        ))

    return RenderedNote(
        chat_id=chat.id,
        platform=chat.platform,
        vault_rel_path=vault_rel,
        markdown=markdown,
        attachments=chat.attachments,
        attachment_stubs=stubs,
    )
