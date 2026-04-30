from datetime import datetime, timezone

from ai_mem.schema import (
    Attachment,
    ContentBlock,
    NormalizedChat,
    NormalizedMessage,
)


def _now() -> datetime:
    return datetime(2025, 11, 7, 12, 0, tzinfo=timezone.utc)


def test_minimal_chat_validates() -> None:
    chat = NormalizedChat(
        id="abc",
        platform="claude",
        title="Hello world",
        created_at=_now(),
        updated_at=_now(),
    )
    assert chat.platform == "claude"
    assert chat.status == "active"
    assert chat.messages == []
    assert chat.has_alternate_branches is False
    assert chat.branch_count == 1


def test_message_with_content_blocks() -> None:
    msg = NormalizedMessage(
        id="m1",
        role="user",
        created_at=_now(),
        content=[
            ContentBlock(kind="text", text="hi"),
            ContentBlock(kind="code", language="python", text="print(1)"),
        ],
    )
    assert msg.role == "user"
    assert msg.content[1].language == "python"


def test_attachment_requires_sha_and_relpath() -> None:
    a = Attachment(
        id="deadbeef",
        kind="user_upload",
        vault_rel_path="AI Chats/attachments/abc/deadbeef-file.pdf",
        sha256="deadbeef",
    )
    assert a.kind == "user_upload"



def test_extra_fields_allowed_for_forward_compat() -> None:
    # Important for schema drift: we shouldn't blow up on unknown keys.
    chat = NormalizedChat.model_validate(
        {
            "id": "abc",
            "platform": "claude",
            "title": "t",
            "created_at": _now(),
            "updated_at": _now(),
            "some_future_field": {"nested": 1},
        }
    )
    assert chat.id == "abc"
