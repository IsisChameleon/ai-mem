"""Copy attachments into the vault. Hash-addressed, size-capped."""

from __future__ import annotations

from pathlib import Path

from ai_mem.schema import Attachment


def copy(src: Path, dest: Path, max_bytes: int) -> Attachment | None:
    """Copy src to dest if size <= max_bytes and dest doesn't already match.
    Return the Attachment record, or None if skipped. Stub."""
    raise NotImplementedError("sync.attachments.copy pending")


def prune_orphans(vault_root: Path, referenced_ids: set[str]) -> list[Path]:
    """Remove attachments under <vault>/AI Chats/attachments/ that no note references.
    Only called when --prune is passed. Stub."""
    raise NotImplementedError("sync.attachments.prune_orphans pending")
