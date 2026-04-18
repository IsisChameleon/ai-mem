"""ChatGPT export parser. Stub.

Expected shape:
  conversations.json: list of conversations, each with
    id, title, create_time, update_time, mapping{node_id: {id, parent, children, message}},
    current_node.
  Messages live under mapping[node].message with author.role and content.content_type.
  We linearize the path root -> current_node. If branches exist off that path,
  set has_alternate_branches=True and branch_count accordingly.
  Attachments: metadata.attachments + loose files in the ZIP.
  Web citations: metadata.citations / content_references (schema drifted, verify).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ai_mem.parse.base import Parser
from ai_mem.schema import NormalizedChat


class ChatGPTParser(Parser):
    platform = "chatgpt"

    def parse(self, export_dir: Path) -> Iterator[NormalizedChat]:
        raise NotImplementedError("parse.chatgpt pending real-export inspection")
