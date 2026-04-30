"""Central orchestration module. Drives the ingest pipeline end-to-end."""

from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ai_mem.config import Config
from ai_mem.fetch.archive import extract
from ai_mem.parse.claude import ClaudeParser
from ai_mem.render.note import render as render_note
from ai_mem.schema import NormalizedChat
from ai_mem.sync.state import ChatStateEntry, LastIngestRecord, SyncState, chat_key, load, save
from ai_mem.sync.writer import write_atomic
from ai_mem.util.hashing import canonical_json_hash

log = logging.getLogger(__name__)


@dataclass
class IngestResult:
    chats_seen: int = 0
    chats_written: int = 0
    chats_skipped: int = 0
    chats_filtered: int = 0
    chats_failed: int = 0
    stubs_written: int = 0
    notes_paths: list[Path] = field(default_factory=list)


def _detect_platform_and_parse(export_dir: Path, account: str | None):
    """Detect the platform from export_dir and return an iterator of NormalizedChat."""
    if (export_dir / "conversations.json").exists():
        return ClaudeParser(account=account).parse(export_dir)
    raise ValueError(
        f"Cannot detect platform from export dir {export_dir!r}. "
        "Only Claude exports (containing conversations.json) are currently supported. "
        "ChatGPT parser is not yet implemented."
    )


def ingest(
    export_path: Path,
    cfg: Config,
    *,
    dry_run: bool = False,
    only_chat_id: str | None = None,
    since: datetime | None = None,
    imported_at: datetime | None = None,
    account: str | None = None,
    no_since: bool = False,
) -> IngestResult:
    """Run the full ingest pipeline for an export path (ZIP or directory).

    Args:
        export_path: Path to a ZIP archive or already-extracted export directory.
        cfg: Loaded Config object.
        dry_run: If True, log planned writes but don't touch disk.
        only_chat_id: If set, process only the chat with this ID.
        since: If set, skip chats updated before this datetime.
        imported_at: Timestamp to record as import time (defaults to now).

    Returns:
        IngestResult with counts of chats processed.
    """
    result = IngestResult()
    _imported_at = imported_at or datetime.now(UTC)
    source_name = export_path.name  # capture before potential ZIP extraction

    # Handle ZIP extraction inside the try/finally so cleanup always runs,
    # including when extract() raises (e.g. ZipSlip).
    tmp_dir_ctx = None
    try:
        if export_path.is_file() and export_path.suffix.lower() == ".zip":
            tmp_dir_ctx = tempfile.TemporaryDirectory()
            dest = Path(tmp_dir_ctx.name)
            extract(export_path, dest)
            export_dir = dest
        else:
            export_dir = export_path

        _run_ingest(
            export_dir=export_dir,
            cfg=cfg,
            result=result,
            dry_run=dry_run,
            only_chat_id=only_chat_id,
            since=since,
            imported_at=_imported_at,
            account=account if account is not None else cfg.account,
            source_name=source_name,
            no_since=no_since,
        )
    finally:
        if tmp_dir_ctx is not None:
            tmp_dir_ctx.cleanup()

    return result


def _run_ingest(
    export_dir: Path,
    cfg: Config,
    result: IngestResult,
    dry_run: bool,
    only_chat_id: str | None,
    since: datetime | None,
    imported_at: datetime,
    account: str | None,
    source_name: str,
    no_since: bool,
) -> None:
    """Core ingest logic after extraction is resolved."""
    state = load(cfg.paths.sync_state)

    # Auto-since: if no explicit --since and not suppressed, use the max
    # chat updated_at from the last run as the filter floor.
    if since is None and not no_since and state.last_ingest is not None:
        since = datetime.fromisoformat(state.last_ingest.max_chat_updated_at)
        log.info(
            "auto-filtering to chats updated after %s (use --no-since to process all)",
            state.last_ingest.max_chat_updated_at,
        )

    chat_iter = _detect_platform_and_parse(export_dir, account)

    # Track the highest updated_at seen across the whole export for the next
    # run's auto-since floor. Updated before the since filter so it reflects
    # the full export, not just the window processed this run.
    max_chat_updated_at: datetime | None = None

    for chat in chat_iter:
        result.chats_seen += 1

        if max_chat_updated_at is None or chat.updated_at > max_chat_updated_at:
            max_chat_updated_at = chat.updated_at

        if only_chat_id is not None and chat.id != only_chat_id:
            result.chats_filtered += 1
            continue

        if since is not None and chat.updated_at < since:
            result.chats_skipped += 1
            continue

        try:
            _process_chat(
                chat=chat,
                cfg=cfg,
                state=state,
                result=result,
                dry_run=dry_run,
                imported_at=imported_at,
            )
        except Exception:
            log.error(
                "Failed to process chat %s:%s — skipping",
                chat.platform,
                chat.id,
                exc_info=True,
            )
            _dump_failed_chat(chat, cfg)
            result.chats_failed += 1

    if not dry_run:
        # Record last_ingest for full runs so the next run can auto-filter.
        # Skipped for --only targeted runs which only see a subset of chats.
        if only_chat_id is None and max_chat_updated_at is not None:
            state.last_ingest = LastIngestRecord(
                at=imported_at.isoformat(),
                source_name=source_name,
                account=account,
                chats_seen=result.chats_seen,
                chats_written=result.chats_written,
                chats_skipped=result.chats_skipped,
                max_chat_updated_at=max_chat_updated_at.isoformat(),
            )
        save(state, cfg.paths.sync_state)


def _process_chat(
    chat: NormalizedChat,
    cfg: Config,
    state: SyncState,
    result: IngestResult,
    dry_run: bool,
    imported_at: datetime,
) -> None:
    """Process a single chat: idempotency check, render, write."""
    content_hash = canonical_json_hash(chat.model_dump(mode="json"))
    key = chat_key(chat.platform, chat.id)

    existing = state.chats.get(key)
    if existing is not None:
        note_abs = cfg.paths.vault / existing.note_path
        if existing.content_hash == content_hash and note_abs.exists():
            log.debug("Skipping unchanged chat %s", key)
            result.chats_skipped += 1
            return

    rendered = render_note(chat, notes_subdir=cfg.paths.notes_subdir, imported_at=imported_at)

    if dry_run:
        log.info(
            "dry-run: would write note %s and %d stubs",
            rendered.vault_rel_path,
            len(rendered.attachment_stubs),
        )
        result.chats_written += 1
        return

    # Write attachment stubs.
    for stub in rendered.attachment_stubs:
        stub_abs = cfg.paths.vault / stub.vault_rel_path
        write_atomic(stub_abs, stub.markdown)
        result.stubs_written += 1

    # Write the note.
    note_abs = cfg.paths.vault / rendered.vault_rel_path
    write_atomic(note_abs, rendered.markdown)

    # Update state.
    state.chats[key] = ChatStateEntry(
        content_hash=content_hash,
        note_path=rendered.vault_rel_path.as_posix(),
        updated_at=chat.updated_at.isoformat(),
        rendered_at=datetime.now(UTC).isoformat(),
        attachment_ids=[a.id for a in chat.attachments],
    )

    result.chats_written += 1
    result.notes_paths.append(note_abs)


def _dump_failed_chat(chat: NormalizedChat, cfg: Config) -> None:
    """Dump a chat that failed to process to the failed directory."""
    try:
        cfg.paths.failed.mkdir(parents=True, exist_ok=True)
        dump_path = cfg.paths.failed / f"{chat.platform}-{chat.id}.json"
        dump_path.write_text(
            json.dumps(chat.model_dump(mode="json"), indent=2, default=str),
            encoding="utf-8",
        )
    except Exception:
        log.error("Could not dump failed chat %s:%s", chat.platform, chat.id, exc_info=True)
