"""Service-layer tests for enterprise domain logic (async)."""

import os
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select

from backend.enterprise import services
from backend.enterprise.database import dispose_db, get_session_factory, init_db
from backend.enterprise.models import AuditLog, Conversation, Message, User
from backend.enterprise.schemas import (
    MessageCreate,
    UserCreate,
    WorkspaceCreate,
)


@pytest.fixture()
def svc_db(tmp_path: Path) -> str:
    path = str(tmp_path / "svc.db")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{path}"
    dispose_db()
    return path


@pytest_asyncio.fixture()
async def session(svc_db: str):
    await init_db()
    factory = get_session_factory()
    async with factory() as s:
        try:
            yield s
            await s.commit()
        except Exception:
            await s.rollback()
            raise


async def _make_user(session, email="u@example.com", username="u", password="password123"):
    return await services.register_user(
        session, UserCreate(email=email, username=username, password=password)
    )


async def test_register_and_authenticate(session) -> None:
    user = await _make_user(session)
    assert user.id
    auth = await services.authenticate_user(session, user.email, "password123")
    assert auth is not None and auth.id == user.id
    assert await services.authenticate_user(session, user.email, "wrong") is None


async def test_tokens_issue_and_refresh(session) -> None:
    user = await _make_user(session, email="tok@example.com", username="tok")
    tokens = services.issue_tokens(user)
    refreshed = await services.refresh_tokens(session, tokens.refresh_token)
    assert refreshed.access_token
    assert refreshed.refresh_token != tokens.refresh_token


async def test_duplicate_registration_conflicts(session) -> None:
    from fastapi import HTTPException

    await _make_user(session, email="dup@example.com", username="dup")
    try:
        await _make_user(session, email="dup@example.com", username="dup2")
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("expected conflict")


async def test_password_reset_flow(session) -> None:
    user = await _make_user(session, email="pr@example.com", username="pr")
    raw = await services.create_password_reset_token(session, user)
    await services.reset_password(session, raw, "newpass456")
    assert await services.authenticate_user(session, user.email, "newpass456") is not None
    # token is single use
    from fastapi import HTTPException

    try:
        await services.reset_password(session, raw, "another789")
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("expected single-use rejection")


async def test_email_verification_flow(session) -> None:
    user = await _make_user(session, email="ev@example.com", username="ev")
    assert user.is_verified is False
    raw = await services.create_email_verification_token(session, user)
    await services.verify_email(session, raw)
    refreshed = await session.get(User, user.id)
    assert refreshed.is_verified is True


async def test_workspace_membership_lifecycle(session) -> None:
    owner = await _make_user(session, email="wo@example.com", username="wo")
    ws = await services.create_workspace(
        session, owner, WorkspaceCreate(name="WS", is_shared_kb=True)
    )
    mine = await services.list_user_workspaces(session, owner)
    assert any(w.id == ws.id for w in mine)

    member = await _make_user(session, email="wm@example.com", username="wm")
    await services.add_workspace_member(session, ws, member.id, "member")
    role = await services.user_workspace_role(session, member.id, ws.id)
    assert role == "member"
    await services.remove_workspace_member(session, ws.id, member.id)
    assert await services.user_workspace_role(session, member.id, ws.id) is None


async def test_conversation_search_by_title_and_content(session) -> None:
    user = await _make_user(session, email="cs@example.com", username="cs")
    conv = await services.create_conversation(session, user, "Blue Whale Topic", None)
    await services.add_message(
        session, conv, MessageCreate(role="user", content="tell me about jellyfish")
    )
    by_title = await services.search_conversations(session, user, "whale")
    assert any(c.id == conv.id for c in by_title)
    by_body = await services.search_conversations(session, user, "jellyfish")
    assert any(c.id == conv.id for c in by_body)
    none = await services.search_conversations(session, user, "unlikelyterm")
    assert none == []


async def test_conversation_rename_and_delete(session) -> None:
    user = await _make_user(session, email="cd@example.com", username="cd")
    conv = await services.create_conversation(session, user, "Old", None)
    await services.rename_conversation(session, conv, "Renamed")
    refreshed = await session.get(Conversation, conv.id)
    assert refreshed.title == "Renamed"
    await services.delete_conversation(session, conv)
    assert await session.get(Conversation, conv.id) is None


async def test_audit_recording_and_listing(session) -> None:
    user = await _make_user(session, email="au@example.com", username="au")
    await services.record_audit(session, action="custom.action", user=user, resource_type="user")
    records = await services.list_audit(session, limit=10)
    assert any(r.action == "custom.action" for r in records)
    count = await session.execute(select(AuditLog))
    assert len(list(count.scalars().all())) >= 1


async def test_compute_stats_counts_entities(session) -> None:
    user = await _make_user(session, email="st@example.com", username="st")
    ws = await services.create_workspace(session, user, WorkspaceCreate(name="S"))
    conv = await services.create_conversation(session, user, "C", ws.id)
    await services.add_message(session, conv, MessageCreate(role="user", content="hi"))
    stats = await services.compute_stats(session)
    assert stats["total_users"] >= 1
    assert stats["total_workspaces"] >= 1
    assert stats["total_conversations"] >= 1
    assert stats["total_messages"] >= 1


async def test_oauth_login_unconfigured_raises(session) -> None:
    from fastapi import HTTPException

    try:
        await services.oauth_login(session, "google", "code")
    except HTTPException as exc:
        assert exc.status_code == 501
    else:
        raise AssertionError("expected not-implemented")
