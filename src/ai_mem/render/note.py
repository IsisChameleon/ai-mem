"""Assemble the full Markdown note. Stub.

Structure:
  ---
  <frontmatter>
  ---
  # <title>
  > [!info] <source> · <model> · <span> · <N> messages · imported <date>
  ## Summary
  <summary>
  ## Sources & artifacts
  ### Uploaded
  ### Generated
  ### Web sources referenced
  ## Conversation
  <transcript>
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_mem.schema import Attachment, NormalizedChat


@dataclass(frozen=True)
class RenderedNote:
    chat_id: str
    platform: str
    vault_rel_path: Path
    markdown: str
    attachments: list[Attachment]


def render(chat: NormalizedChat, notes_subdir: str) -> RenderedNote:
    raise NotImplementedError("render.note.render pending transcript + sections implementation")
