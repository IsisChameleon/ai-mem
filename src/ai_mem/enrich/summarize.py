"""Per-chat summary + topic extraction via Claude Haiku 4.5.

One small call per new/changed chat. Prompt asks for:
  - 2-3 sentence summary (plain prose, first sentence = current state)
  - 3-5 topic strings
  - status hint: active | stale | resolved
Returns SummaryResult.
"""

from __future__ import annotations

from ai_mem.config import LLM
from ai_mem.schema import NormalizedChat, SummaryResult


def summarize(chat: NormalizedChat, llm: LLM) -> SummaryResult:
    raise NotImplementedError("enrich.summarize.summarize pending")
