"""Load and save .sync-state.json. Drives idempotency.

Shape:
  {
    "version": 1,
    "last_ingest": {
      "at": "2026-04-30T18:45:26Z",
      "source_name": "claude-export.zip",
      "account": "me@example.com",
      "chats_seen": 34,
      "chats_written": 2,
      "chats_skipped": 32,
      "max_chat_updated_at": "2026-04-29T10:00:00Z"
    },
    "chats": {
       "<platform>:<chat_id>": {
         "content_hash": "...",
         "note_path": "AI Chats/claude/2025-11/2025-11-07 - slug.md",
         "updated_at": "...",
         "rendered_at": "...",
         "attachment_ids": [...]
       }
    },
    "processed_emails": {
       "<gmail_message_id>": {"platform": "claude", "received_at": "...", "zip_path": "..."}
    }
  }
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class ChatStateEntry:
    content_hash: str
    note_path: str
    updated_at: str
    rendered_at: str
    attachment_ids: list[str] = field(default_factory=list)


@dataclass
class EmailStateEntry:
    platform: str
    received_at: str
    zip_path: str


@dataclass
class LastIngestRecord:
    at: str                   # ISO timestamp when the run started
    source_name: str          # basename of the ZIP or export dir
    account: str | None       # account email used
    chats_seen: int
    chats_written: int
    chats_skipped: int
    max_chat_updated_at: str  # floor for next run's auto-since filter


@dataclass
class SyncState:
    version: int = 1
    last_ingest: LastIngestRecord | None = None
    chats: dict[str, ChatStateEntry] = field(default_factory=dict)
    processed_emails: dict[str, EmailStateEntry] = field(default_factory=dict)


def load(path: Path) -> SyncState:
    if not path.exists():
        return SyncState()
    raw = json.loads(path.read_text())
    li_raw = raw.get("last_ingest")
    return SyncState(
        version=raw.get("version", 1),
        last_ingest=LastIngestRecord(**li_raw) if li_raw else None,
        chats={
            k: ChatStateEntry(
                content_hash=v["content_hash"],
                note_path=v["note_path"],
                updated_at=v["updated_at"],
                rendered_at=v["rendered_at"],
                attachment_ids=v.get("attachment_ids", []),
            )
            for k, v in raw.get("chats", {}).items()
        },
        processed_emails={
            k: EmailStateEntry(**v) for k, v in raw.get("processed_emails", {}).items()
        },
    )


def save(state: SyncState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(
            {
                "version": state.version,
                "last_ingest": asdict(state.last_ingest) if state.last_ingest else None,
                "chats": {k: asdict(v) for k, v in state.chats.items()},
                "processed_emails": {
                    k: asdict(v) for k, v in state.processed_emails.items()
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    tmp.replace(path)


def chat_key(platform: str, chat_id: str) -> str:
    return f"{platform}:{chat_id}"
