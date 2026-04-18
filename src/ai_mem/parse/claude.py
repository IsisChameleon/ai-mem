"""Claude.ai export parser. Stub — awaits a real export ZIP.

Expected shape (to be confirmed against real data):
  conversations.json: list of conversations, each with
    uuid, name, created_at, updated_at, chat_messages[]
  chat_messages[*]: uuid, text, sender ("human"|"assistant"), created_at,
    attachments[], files_v2[]
  Artifacts appear inline in assistant text as <antArtifact> tags — TBD whether
  literal or stripped in the export.
  Attachments may be loose files alongside conversations.json (needs verification).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ai_mem.parse.base import Parser
from ai_mem.schema import NormalizedChat


class ClaudeParser(Parser):
    platform = "claude"

    def parse(self, export_dir: Path) -> Iterator[NormalizedChat]:
        raise NotImplementedError("parse.claude pending real-export inspection")
