"""argparse entrypoint. Wires stages together once implemented."""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

from ai_mem import __version__
from ai_mem.config import load as load_config
from ai_mem.util.logging import setup as setup_logging

log = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ai-mem",
        description="Sync Claude.ai and ChatGPT exports into an Obsidian vault.",
    )
    p.add_argument("--version", action="version", version=f"ai-mem {__version__}")
    p.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to config.yaml (default: ./config.yaml)",
    )
    p.add_argument("--dry-run", action="store_true", help="Render but don't write to the vault.")
    p.add_argument("--only", metavar="CHAT_ID", help="Process only this chat id.")
    p.add_argument("--since", metavar="ISO_DATE", help="Skip chats updated before this date.")
    p.add_argument("--prune", action="store_true", help="Remove orphaned attachments.")

    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--fetch", action="store_true", help="Pull new exports from Gmail.")
    mode.add_argument(
        "--ingest",
        metavar="PATH",
        type=Path,
        help="Process a specific export ZIP or already-extracted directory.",
    )
    return p


def _parse_since(value: str | None) -> datetime | None:
    """Parse --since as YYYY-MM-DD or full ISO datetime, returning a tz-aware UTC datetime."""
    if value is None:
        return None
    # Try full ISO first, then date-only.
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            continue
    raise ValueError(f"Cannot parse --since value: {value!r}. Use YYYY-MM-DD or ISO format.")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    cfg = load_config(args.config)
    setup_logging(cfg.logging.level, cfg.logging.json)

    if args.fetch:
        raise SystemExit("fetch mode not yet implemented")

    if args.ingest:
        from ai_mem.pipeline import ingest

        if args.prune:
            log.warning("prune not yet supported — ignoring --prune flag")

        since = _parse_since(args.since)

        result = ingest(
            export_path=args.ingest,
            cfg=cfg,
            dry_run=args.dry_run,
            only_chat_id=args.only,
            since=since,
        )

        log.info(
            "ingest: seen=%d written=%d skipped=%d failed=%d stubs=%d",
            result.chats_seen,
            result.chats_written,
            result.chats_skipped,
            result.chats_failed,
            result.stubs_written,
        )

        return 1 if result.chats_failed > 0 else 0

    raise SystemExit("specify --fetch or --ingest <path>")


if __name__ == "__main__":
    raise SystemExit(main())
