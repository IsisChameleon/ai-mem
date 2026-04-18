"""Parser protocol. Each platform implements parse(export_dir) -> list[NormalizedChat]."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Protocol

from ai_mem.schema import NormalizedChat, Platform


class Parser(Protocol):
    platform: Platform

    def parse(self, export_dir: Path) -> Iterator[NormalizedChat]:
        """Yield one NormalizedChat per conversation in the export.

        Must not raise on a single bad chat; log + continue. Raising here aborts
        the whole batch, so only raise on catastrophic errors (missing file,
        unreadable JSON).
        """
        ...
