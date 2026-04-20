"""Render the interleaved transcript section of a note."""

from __future__ import annotations

from datetime import UTC

from ai_mem.schema import ContentBlock, NormalizedChat, NormalizedMessage, WebCitation

_ROLE_EMOJI = {
    "user": "👤",
    "assistant": "🤖",
    "system": "⚙️",
    "tool": "🔧",
}


def _short(id_: str) -> str:
    """Return first 6 hex chars of an id."""
    return id_[:6]


def _human_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes // 1024} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _render_block(block: ContentBlock, citation_ids: list[str]) -> str:
    kind = block.kind

    if kind == "text":
        text = block.text or ""
        if citation_ids:
            refs = ", ".join(f"[^c-{_short(cid)}]" for cid in citation_ids)
            text = f"{text}\n\n*Cites:* {refs}"
        return text

    if kind == "code":
        lang = block.language or ""
        return f"```{lang}\n{block.text or ''}\n```"

    if kind == "thinking":
        return (
            "<details>\n"
            "<summary>Thinking</summary>\n"
            "\n"
            f"{block.text or ''}\n"
            "\n"
            "</details>"
        )

    if kind == "tool_call":
        return f"**Tool call:**\n\n```json\n{block.text or ''}\n```"

    if kind == "tool_result":
        text = block.text or ""
        stripped = text.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            return f"**Tool result:**\n\n```json\n{text}\n```"
        return f"**Tool result:**\n\n{text}"

    if kind == "image_ref":
        ref = block.ref_id or "ref"
        path = ""
        return f"[image_ref: {ref}]({path})"

    if kind == "artifact_ref":
        ref = block.ref_id or "ref"
        path = ""
        return f"[artifact_ref: {ref}]({path})"

    # Fallback — shouldn't happen with known kinds
    return f"<!-- unknown block kind: {kind} -->"


def _render_message(msg: NormalizedMessage) -> str:
    emoji = _ROLE_EMOJI.get(msg.role, "❓")
    role_label = msg.role.capitalize()
    ts = msg.created_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")

    parts = [f"### {emoji} {role_label}", f"_{ts}_"]

    # Only the text block gets citation_ids; other blocks don't
    # citation_ids belong to the message and are appended on text blocks
    text_block_found = any(b.kind == "text" for b in msg.content)
    for block in msg.content:
        if block.kind == "text" and text_block_found:
            rendered = _render_block(block, msg.citation_ids)
        else:
            rendered = _render_block(block, [])
        parts.append(rendered)

    return "\n\n".join(parts)


def _collect_citations_in_order(
    chat: NormalizedChat,
) -> list[WebCitation]:
    """Return WebCitation objects in order of first-cite appearance."""
    by_id = {ws.id: ws for ws in chat.web_sources}
    seen: list[str] = []
    for msg in chat.messages:
        for cid in msg.citation_ids:
            if cid not in seen:
                seen.append(cid)
    return [by_id[cid] for cid in seen if cid in by_id]


def _render_footnote(citation: WebCitation) -> str:
    label = citation.title or citation.url
    ref = f"[^c-{_short(citation.id)}]: [{label}]({citation.url})"
    if citation.accessed_at:
        date_str = citation.accessed_at.astimezone(UTC).strftime("%Y-%m-%d")
        ref += f" — accessed {date_str}"
    return ref


def render(chat: NormalizedChat) -> str:
    """Render the conversation section markdown."""
    sections = ["## Conversation"]

    for msg in chat.messages:
        sections.append(_render_message(msg))

    body = "\n\n".join(sections)

    ordered_citations = _collect_citations_in_order(chat)
    if ordered_citations:
        footnotes = "\n".join(_render_footnote(c) for c in ordered_citations)
        body = f"{body}\n\n{footnotes}"

    return body
