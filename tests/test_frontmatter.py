from datetime import datetime, timezone

import yaml

from ai_mem.render.frontmatter import FRONTMATTER_KEYS, build, to_yaml_block
from ai_mem.schema import NormalizedChat


def _chat() -> NormalizedChat:
    dt = datetime(2025, 11, 7, 15, 30, tzinfo=timezone.utc)
    return NormalizedChat(
        id="abc123",
        platform="claude",
        title="Example",
        model="claude-sonnet-4-6",
        account="test@example.com",
        url="https://claude.ai/chat/abc123",
        created_at=dt,
        updated_at=dt,
    )


def test_build_has_all_expected_keys_in_order() -> None:
    imported = datetime(2025, 11, 7, 16, 0, tzinfo=timezone.utc)
    fm = build(_chat(), imported_at=imported)
    assert list(fm.keys()) == FRONTMATTER_KEYS


def test_yaml_block_is_parseable() -> None:
    block = to_yaml_block(_chat(), imported_at=datetime(2025, 11, 7, 16, 0, tzinfo=timezone.utc))
    assert block.startswith("---\n")
    assert block.endswith("---\n")
    inner = block.strip().strip("-").strip()
    data = yaml.safe_load(inner)
    assert data["id"] == "abc123"
    assert data["platform"] == "claude"
    assert data["account"] == "test@example.com"
    assert data["message_count"] == 0
    assert data["created"].endswith("Z")


def test_iso_timestamps_are_utc_z() -> None:
    block = to_yaml_block(_chat())
    inner = block.strip().strip("-").strip()
    data = yaml.safe_load(inner)
    assert data["created"] == "2025-11-07T15:30:00Z"
