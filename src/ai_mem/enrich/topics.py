"""Topic normalization against topics.yaml.

Controlled vocabulary: canonical slug -> {aliases}. Unknown topics from the LLM
are kept as free-form strings so nothing gets lost; the dashboard surfaces them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class TopicVocabulary:
    canonical: dict[str, list[str]] = field(default_factory=dict)

    @property
    def alias_to_canonical(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for slug, aliases in self.canonical.items():
            out[slug.lower()] = slug
            for a in aliases:
                out[a.lower()] = slug
        return out


def load(path: Path) -> TopicVocabulary:
    raw = yaml.safe_load(path.read_text()) or {}
    topics = raw.get("topics") or {}
    canonical = {
        slug: list((spec or {}).get("aliases", []))
        for slug, spec in topics.items()
    }
    return TopicVocabulary(canonical=canonical)


def normalize(raw_topics: list[str], vocab: TopicVocabulary) -> list[str]:
    """Map raw LLM topics to canonical slugs where known; keep free-form otherwise.
    Deduplicate preserving first-seen order."""
    alias = vocab.alias_to_canonical
    out: list[str] = []
    seen: set[str] = set()
    for t in raw_topics:
        key = t.strip().lower()
        canonical = alias.get(key, t.strip())
        if canonical and canonical not in seen:
            seen.add(canonical)
            out.append(canonical)
    return out
