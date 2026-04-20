"""Claude.ai export parser.

Consumes an export directory containing conversations.json and yields one
NormalizedChat per conversation. Per-chat failures are isolated — a bad
conversation logs a warning and continues; only missing/unreadable
conversations.json raises.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from ai_mem.parse.base import Parser
from ai_mem.render.filenames import attachment_filename, attachment_relpath
from ai_mem.schema import (
    Attachment,
    ContentBlock,
    NormalizedChat,
    NormalizedMessage,
    WebCitation,
)
from ai_mem.util.hashing import short_id

log = logging.getLogger(__name__)

_NOTES_SUBDIR = "AI Chats"

_FILE_TYPE_TO_MIME: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}


def _sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _parse_dt(s: str) -> datetime:
    """Parse an ISO-8601 string into a timezone-aware UTC datetime."""
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _mime_from_file_type_or_name(file_type: str, file_name: str) -> str | None:
    ft = (file_type or "").lower().strip()
    if ft in _FILE_TYPE_TO_MIME:
        return _FILE_TYPE_TO_MIME[ft]
    # Fall back to filename extension
    ext = Path(file_name).suffix.lower().lstrip(".")
    return _FILE_TYPE_TO_MIME.get(ext)


def _attachment_id(file_name: str, file_size: int, extracted_content: str | None) -> str:
    key = f"{file_name}|{file_size}|{extracted_content or ''}"
    return short_id(_sha256_str(key))


def _build_attachment(
    chat_id: str,
    file_name: str,
    file_size: int,
    file_type: str,
    extracted_content: str | None,
) -> Attachment:
    att_id = _attachment_id(file_name, file_size, extracted_content)
    mime = _mime_from_file_type_or_name(file_type, file_name)
    full_sha = _sha256_str(f"{file_name}|{file_size}|{extracted_content or ''}")
    fname = attachment_filename(full_sha, file_name, mime)
    vpath = attachment_relpath(chat_id, fname, _NOTES_SUBDIR)
    return Attachment(
        id=att_id,
        kind="user_upload",
        original_filename=file_name,
        mime_type=mime,
        size_bytes=file_size,
        source_path=None,
        vault_rel_path=vpath,
        sha256=full_sha,
        extracted_content=extracted_content,
    )


def _parse_message(
    raw: dict,
    chat_id: str,
    chat_attachments_by_id: dict[str, Attachment],
) -> tuple[NormalizedMessage, list[Attachment]]:
    """Parse a raw message dict.

    Returns the NormalizedMessage and any new Attachment objects discovered
    in this message that weren't already in chat_attachments_by_id.
    """
    new_attachments: list[Attachment] = []
    attachment_ids: list[str] = []
    citation_ids: list[str] = []
    content_blocks: list[ContentBlock] = []

    # -- attachments[] (have extracted_content) --
    for raw_att in raw.get("attachments", []):
        att = _build_attachment(
            chat_id=chat_id,
            file_name=raw_att["file_name"],
            file_size=raw_att.get("file_size", 0),
            file_type=raw_att.get("file_type", ""),
            extracted_content=raw_att.get("extracted_content"),
        )
        attachment_ids.append(att.id)
        if att.id not in chat_attachments_by_id:
            chat_attachments_by_id[att.id] = att
            new_attachments.append(att)

    # -- files[] (pointer refs — may have no corresponding attachment entry) --
    for raw_file in raw.get("files", []):
        fname = raw_file.get("file_name", "")
        # files-only refs have no size/type/content info; use 0 / "" / None
        att = _build_attachment(
            chat_id=chat_id,
            file_name=fname,
            file_size=0,
            file_type="",
            extracted_content=None,
        )
        if att.id not in chat_attachments_by_id:
            chat_attachments_by_id[att.id] = att
            new_attachments.append(att)
        if att.id not in attachment_ids:
            attachment_ids.append(att.id)

    # -- content blocks --
    for blk in raw.get("content", []):
        block_type = blk.get("type", "")

        if block_type == "text":
            text = blk.get("text", "")
            block = ContentBlock(kind="text", text=text)
            content_blocks.append(block)
            for cit in blk.get("citations", []):
                url = cit.get("details", {}).get("url", "")
                if url:
                    cit_id = short_id(_sha256_str(url))
                    if cit_id not in citation_ids:
                        citation_ids.append(cit_id)

        elif block_type == "thinking":
            thinking_text = blk.get("thinking", "")
            block = ContentBlock(kind="thinking", text=thinking_text)
            content_blocks.append(block)

        elif block_type == "tool_use":
            payload = json.dumps(
                {"name": blk.get("name", ""), "input": blk.get("input", {})},
                sort_keys=True,
            )
            block = ContentBlock(kind="tool_call", text=payload, language="json")
            content_blocks.append(block)

        elif block_type == "tool_result":
            parts = [
                item.get("text", "")
                for item in blk.get("content", [])
                if isinstance(item, dict)
            ]
            combined = "\n".join(p for p in parts if p)
            block = ContentBlock(kind="tool_result", text=combined)
            content_blocks.append(block)

        else:
            log.warning(
                "Unknown content block type %r in message %s — skipping",
                block_type,
                raw.get("uuid", "?"),
            )

    role_map = {"human": "user", "assistant": "assistant"}
    raw_role = raw.get("sender", "human")
    role = role_map.get(raw_role, raw_role)  # type: ignore[arg-type]

    msg = NormalizedMessage(
        id=raw["uuid"],
        role=role,
        created_at=_parse_dt(raw["created_at"]),
        content=content_blocks,
        attachment_ids=attachment_ids,
        citation_ids=citation_ids,
    )
    return msg, new_attachments


def _parse_conversation(raw: dict) -> NormalizedChat:
    """Parse a single conversation dict into NormalizedChat."""
    chat_id = raw["uuid"]
    attachments_by_id: dict[str, Attachment] = {}
    web_sources_by_id: dict[str, WebCitation] = {}
    messages: list[NormalizedMessage] = []

    for raw_msg in raw["chat_messages"]:
        msg, _new_atts = _parse_message(raw_msg, chat_id, attachments_by_id)
        messages.append(msg)

        # Collect citations into web_sources (keyed by url hash)
        for raw_blk in raw_msg.get("content", []):
            if raw_blk.get("type") != "text":
                continue
            for cit in raw_blk.get("citations", []):
                url = cit.get("details", {}).get("url", "")
                if not url:
                    continue
                cit_id = short_id(_sha256_str(url))
                if cit_id not in web_sources_by_id:
                    web_sources_by_id[cit_id] = WebCitation(
                        id=cit_id,
                        url=url,
                        cited_in_message_id=raw_msg["uuid"],
                    )

    return NormalizedChat(
        id=chat_id,
        platform="claude",
        title=raw.get("name") or "Untitled",
        model=None,
        url=f"https://claude.ai/chat/{chat_id}",
        created_at=_parse_dt(raw["created_at"]),
        updated_at=_parse_dt(raw["updated_at"]),
        messages=messages,
        attachments=list(attachments_by_id.values()),
        artifacts=[],
        web_sources=list(web_sources_by_id.values()),
        has_alternate_branches=False,
        branch_count=1,
    )


class ClaudeParser(Parser):
    platform = "claude"

    def parse(self, export_dir: Path) -> Iterator[NormalizedChat]:
        conversations_path = export_dir / "conversations.json"
        if not conversations_path.exists():
            raise FileNotFoundError(
                f"conversations.json not found in {export_dir}"
            )

        raw_list = json.loads(conversations_path.read_text(encoding="utf-8"))

        for raw_conv in raw_list:
            conv_uuid = raw_conv.get("uuid", "<unknown>")
            try:
                yield _parse_conversation(raw_conv)
            except Exception:
                log.warning(
                    "Skipping conversation %s due to parse error",
                    conv_uuid,
                    exc_info=True,
                )
