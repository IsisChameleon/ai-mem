"""YAML frontmatter builder. Stable key order so golden-file tests don't churn."""

from __future__ import annotations

from datetime import datetime, timezone

import yaml

from ai_mem.schema import NormalizedChat

FRONTMATTER_KEYS = [
    "id",
    "title",
    "platform",
    "model",
    "account",
    "url",
    "created",
    "updated",
    "imported",
    "message_count",
    "status",
    "has_alternate_branches",
    "branch_count",
]


def build(chat: NormalizedChat, imported_at: datetime | None = None) -> dict:
    imported = imported_at or datetime.now(timezone.utc)
    data = {
        "id": chat.id,
        "title": chat.title,
        "platform": chat.platform,
        "model": chat.model,
        "account": chat.account,
        "url": chat.url,
        "created": _iso(chat.created_at),
        "updated": _iso(chat.updated_at),
        "imported": _iso(imported),
        "message_count": len(chat.messages),
        "status": chat.status,
        "has_alternate_branches": chat.has_alternate_branches,
        "branch_count": chat.branch_count,
    }
    # Enforce key order.
    return {k: data[k] for k in FRONTMATTER_KEYS if k in data}


def to_yaml_block(chat: NormalizedChat, imported_at: datetime | None = None) -> str:
    body = yaml.safe_dump(
        build(chat, imported_at),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    return f"---\n{body}---\n"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
