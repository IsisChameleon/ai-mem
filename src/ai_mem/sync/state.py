"""Load and save .sync-state.json. Drives idempotency.

Shape:
  {
    "version": 1,
    "topics_version": "<sha256 of topics.yaml>",
    "chats": {
       "<platform>:<chat_id>": {
         "content_hash": "...",
         "summary_hash": "...",
         "note_path": "AI Chats/claude/2025-11/2025-11-07 - slug.md",
         "updated_at": "...",
         "rendered_at": "...",
         "attachment_ids": [...],
         "summary_pending": false
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
    summary_hash: str
    note_path: str
    updated_at: str
    rendered_at: str
    attachment_ids: list[str] = field(default_factory=list)
    summary_pending: bool = False


@dataclass
class EmailStateEntry:
    platform: str
    received_at: str
    zip_path: str


@dataclass
class SyncState:
    version: int = 1
    topics_version: str = ""
    chats: dict[str, ChatStateEntry] = field(default_factory=dict)
    processed_emails: dict[str, EmailStateEntry] = field(default_factory=dict)


def load(path: Path) -> SyncState:
    if not path.exists():
        return SyncState()
    raw = json.loads(path.read_text())
    return SyncState(
        version=raw.get("version", 1),
        topics_version=raw.get("topics_version", ""),
        chats={k: ChatStateEntry(**v) for k, v in raw.get("chats", {}).items()},
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
                "topics_version": state.topics_version,
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
