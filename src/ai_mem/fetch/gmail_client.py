"""Gmail client. Read-only OAuth; finds export-ready emails and downloads ZIPs.

Processed message ids are tracked in .sync-state.json (processed_emails key)
so we don't need gmail.modify scope to avoid re-download.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from ai_mem.config import Gmail


@dataclass(frozen=True)
class FetchedExport:
    platform: str
    message_id: str
    zip_path: Path
    received_at: str


class GmailClient:
    def __init__(self, cfg: Gmail) -> None:
        self.cfg = cfg

    def authorize(self) -> None:
        """Run OAuth flow; cache token at cfg.token. Stub."""
        raise NotImplementedError("fetch.gmail_client.authorize pending")

    def search(self) -> Iterator[str]:
        """Yield message ids matching cfg.query. Stub."""
        raise NotImplementedError("fetch.gmail_client.search pending")

    def download(self, message_id: str, dest_dir: Path) -> FetchedExport | None:
        """Download the ZIP attachment for a given message. Stub."""
        raise NotImplementedError("fetch.gmail_client.download pending")
