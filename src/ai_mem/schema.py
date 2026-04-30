"""Normalized schema. All parsers emit these; all renderers consume them."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Platform = Literal["claude", "chatgpt"]
Role = Literal["user", "assistant", "system", "tool"]
ContentKind = Literal["text", "code", "image_ref", "tool_call", "tool_result", "artifact_ref", "thinking"]
AttachmentKind = Literal["user_upload", "generated", "image"]
ChatStatus = Literal["active", "stale", "resolved"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=False)


class ContentBlock(_Model):
    kind: ContentKind
    text: str | None = None
    language: str | None = None
    ref_id: str | None = None


class Attachment(_Model):
    id: str
    kind: AttachmentKind
    original_filename: str | None = None
    mime_type: str | None = None
    size_bytes: int = 0
    source_path: Path | None = None
    vault_rel_path: Path
    uploaded_at: datetime | None = None
    sha256: str
    skipped_reason: str | None = None
    extracted_content: str | None = None


class Artifact(_Model):
    id: str
    title: str
    kind: str
    language: str | None = None
    source: Literal["message_inline", "tool_output"]
    created_at: datetime
    content: str
    sha256: str


class WebCitation(_Model):
    id: str
    url: str
    title: str | None = None
    accessed_at: datetime | None = None
    cited_in_message_id: str
    context_excerpt: str = ""


class NormalizedMessage(_Model):
    id: str
    role: Role
    created_at: datetime
    content: list[ContentBlock] = Field(default_factory=list)
    attachment_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)


class NormalizedChat(_Model):
    id: str
    platform: Platform
    title: str
    model: str | None = None
    url: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[NormalizedMessage] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    web_sources: list[WebCitation] = Field(default_factory=list)
    raw_path: Path | None = None
    account: str | None = None
    status: ChatStatus = "active"
    # ChatGPT-only: was the mapping tree branched?
    has_alternate_branches: bool = False
    branch_count: int = 1


