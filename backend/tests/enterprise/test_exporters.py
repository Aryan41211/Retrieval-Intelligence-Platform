"""Unit tests for conversation exporters (JSON, Markdown, PDF)."""

from datetime import datetime, timezone

from backend.enterprise.exporters import export_conversation
from backend.enterprise.models import Conversation, Message


def _make_conversation() -> tuple[Conversation, list[Message]]:
    conv = Conversation(
        id="c-1",
        user_id="u-1",
        workspace_id=None,
        title="My Chat",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    messages = [
        Message(
            id="m-1",
            conversation_id="c-1",
            role="user",
            content="Hello there",
            citations={},
            correlation_id=None,
            token_count=3,
            created_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        ),
        Message(
            id="m-2",
            conversation_id="c-1",
            role="assistant",
            content="Hi! How can I help?",
            citations={"doc": "x"},
            correlation_id="corr-1",
            token_count=5,
            created_at=datetime(2024, 1, 1, 12, 1, tzinfo=timezone.utc),
        ),
    ]
    return conv, messages


def test_export_json_contains_messages_and_metadata() -> None:
    conv, messages = _make_conversation()
    content, media_type, filename = export_conversation(conv, messages, "json")
    assert media_type == "application/json"
    assert filename == "My_Chat.json"
    import json

    data = json.loads(content.decode("utf-8"))
    assert data["id"] == "c-1"
    assert data["title"] == "My Chat"
    assert len(data["messages"]) == 2
    assert data["messages"][1]["role"] == "assistant"
    assert data["messages"][1]["citations"] == {"doc": "x"}


def test_export_markdown_renders_roles_and_content() -> None:
    conv, messages = _make_conversation()
    content, media_type, filename = export_conversation(conv, messages, "markdown")
    assert media_type == "text/markdown"
    assert filename == "My_Chat.markdown"
    text = content.decode("utf-8")
    assert "# My Chat" in text
    assert "**User**" in text
    assert "Hello there" in text
    assert "**Assistant**" in text


def test_export_pdf_produces_valid_header() -> None:
    conv, messages = _make_conversation()
    content, media_type, filename = export_conversation(conv, messages, "pdf")
    assert media_type == "application/pdf"
    assert filename == "My_Chat.pdf"
    assert content[:5] == b"%PDF-"


def test_export_rejects_unsupported_format() -> None:
    conv, messages = _make_conversation()
    try:
        export_conversation(conv, messages, "xml")
    except ValueError as exc:
        assert "Unsupported export format" in str(exc)
    else:
        raise AssertionError("expected ValueError")
