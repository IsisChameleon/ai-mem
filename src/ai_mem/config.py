"""Config loader. YAML file → typed Config dataclass with ~/ expansion."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Paths:
    vault: Path
    notes_subdir: str
    raw_archive: Path
    failed: Path
    sync_state: Path
    topics: Path


@dataclass(frozen=True)
class Attachments:
    max_bytes: int = 50 * 1024 * 1024


@dataclass(frozen=True)
class Gmail:
    credentials: Path
    token: Path
    scope: str
    query: str


@dataclass(frozen=True)
class LLM:
    provider: str
    model: str
    api_key_env: str
    max_tokens: int = 400

    @property
    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env)


@dataclass(frozen=True)
class Logging:
    level: str = "INFO"
    json: bool = False


@dataclass(frozen=True)
class Config:
    paths: Paths
    attachments: Attachments
    gmail: Gmail
    llm: LLM
    logging: Logging = field(default_factory=Logging)


def _p(s: str) -> Path:
    return Path(os.path.expanduser(s)).resolve()


def load(path: Path | str) -> Config:
    data = yaml.safe_load(Path(path).read_text())
    p = data["paths"]
    g = data["gmail"]
    m = data["llm"]
    a = data.get("attachments", {})
    lg = data.get("logging", {})
    return Config(
        paths=Paths(
            vault=_p(p["vault"]),
            notes_subdir=p.get("notes_subdir", "AI Chats"),
            raw_archive=_p(p["raw_archive"]),
            failed=_p(p["failed"]),
            sync_state=_p(p["sync_state"]),
            topics=_p(p["topics"]),
        ),
        attachments=Attachments(max_bytes=int(a.get("max_bytes", 50 * 1024 * 1024))),
        gmail=Gmail(
            credentials=_p(g["credentials"]),
            token=_p(g["token"]),
            scope=g["scope"],
            query=g["query"],
        ),
        llm=LLM(
            provider=m["provider"],
            model=m["model"],
            api_key_env=m["api_key_env"],
            max_tokens=int(m.get("max_tokens", 400)),
        ),
        logging=Logging(
            level=lg.get("level", "INFO"),
            json=bool(lg.get("json", False)),
        ),
    )
