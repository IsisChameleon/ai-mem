"""Render the interleaved transcript section. Stub.

Will emit role headers, timestamps, code blocks (language-tagged), attachment
links, artifact references, and citation footnotes.
"""

from __future__ import annotations

from ai_mem.schema import NormalizedChat


def render(chat: NormalizedChat) -> str:
    raise NotImplementedError("render.transcript.render pending real-export validation")
