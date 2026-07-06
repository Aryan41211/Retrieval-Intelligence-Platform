"""
Enterprise service layer: authentication, user management, workspaces,
conversations and audit logging.

Functions are stateless and accept an ``AsyncSession`` so they are easy to unit
test against an in-memory SQLite database.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.enterprise import security
from backend.enterprise.config import get_enterprise_settings
from backend.enterprise.models import (
    AuditLog,
    Conversation,
    EmailVerificationToken,
    Message,
    PasswordResetToken,
    User,
    Workspace,
    WorkspaceMembership,
)
from backend.enterprise.oauth import exchange_code, is_oauth_configured
from backend.enterprise.rbac import Role, permissions_for_role
from backend.enterprise.schemas import (
    MessageCreate,
    TokenResponse,
    UserCreate,
    UserProfileUpdate,
    WorkspaceCreate,
)

settings = get_enterprise_settings()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
async def register_user(db: AsyncSession, data: UserCreate) -> User:
    """Register a new user and return the persisted account."""
    if not settings.registration_enabled:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registration disabled")
    existing = await db.execute(
        select(User).where(or_(User.email == data.email, User.username == data.username))
    )
    if existing.scalar_one_or_none() is not None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    user = User(
        email=data.email,
        username=data.username,
        full_name=data.full_name or "",
        hashed_password=security.hash_password(data.password),
        role=settings.default_role,
        is_verified=not settings.email_verification_required,
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(db: AsyncSession, identifier: str, password: str) -> User | None:
    """Return the user for valid credentials, else ``None``."""
    result = await db.execute(
        select(User).where(or_(User.email == identifier, User.username == identifier))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    if not security.verify_password(password, user.hashed_password):
        return None
    if settings.email_verification_required and not user.is_verified:
        return None
    return user


def issue_tokens(user: User) -> TokenResponse:
    """Issue a new access/refresh token pair for a user."""
    return TokenResponse(
        access_token=security.create_access_token(subject=user.id, role=user.role),
        refresh_token=security.create_refresh_token(subject=user.id),
        expires_in=settings.access_token_ttl_seconds,
    )


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
    """Validate a refresh token and rotate a new token pair."""
    from jwt import PyJWTError

    try:
        payload = security.decode_token(refresh_token, "refresh")
    except PyJWTError:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = await db.get(User, payload["sub"])
    if user is None or not user.is_active:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return issue_tokens(user)


def _send_email(to: str, subject: str, body: str) -> None:
    """Best-effort outbound email placeholder (wire to SMTP in production)."""
    if settings.smtp_host:
        # SMTP send would happen here using smtp_host/smtp_from.
        pass
    import logging

    logging.getLogger(__name__).info("email (not sent in dev): to=%s subject=%s", to, subject)


async def create_password_reset_token(db: AsyncSession, user: User) -> str:
    """Create and persist a single-use password reset token; returns the raw token."""
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(seconds=settings.password_reset_ttl_seconds)
    record = PasswordResetToken(
        user_id=user.id, token_hash=security.hash_token(token), expires_at=expires
    )
    db.add(record)
    await db.flush()
    return token


async def request_password_reset(db: AsyncSession, email: str) -> None:
    """Create a reset token and 'send' it (logged in dev)."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        return  # do not reveal whether the email exists
    token = await create_password_reset_token(db, user)
    _send_email(user.email, "Password reset", f"Reset token: {token}")


async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
    """Consume a reset token and update the user's password."""
    from fastapi import HTTPException, status

    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == security.hash_token(token))
    )
    record = result.scalar_one_or_none()
    if record is None or record.used_at is not None or record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    user = await db.get(User, record.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    user.hashed_password = security.hash_password(new_password)
    record.used_at = datetime.now(timezone.utc)
    await db.flush()


async def create_email_verification_token(db: AsyncSession, user: User) -> str:
    """Create and persist an email verification token; returns the raw token."""
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(seconds=settings.email_verification_ttl_seconds)
    record = EmailVerificationToken(
        user_id=user.id, token_hash=security.hash_token(token), expires_at=expires
    )
    db.add(record)
    await db.flush()
    return token


async def verify_email(db: AsyncSession, token: str) -> None:
    """Consume an email verification token."""
    from fastapi import HTTPException, status

    result = await db.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == security.hash_token(token)
        )
    )
    record = result.scalar_one_or_none()
    if record is None or record.used_at is not None or record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    user = await db.get(User, record.user_id)
    if user is not None:
        user.is_verified = True
    record.used_at = datetime.now(timezone.utc)
    await db.flush()


async def oauth_login(db: AsyncSession, provider: str, code: str) -> TokenResponse:
    """Exchange an OAuth code for a local account and issue tokens."""
    if not is_oauth_configured(provider):
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="OAuth not configured")
    profile = await exchange_code(provider, code)
    email = profile.get("email")
    if not email:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth missing email")
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        if not settings.registration_enabled:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registration disabled")
        user = User(
            email=email,
            username=email.split("@")[0],
            full_name=profile.get("full_name", ""),
            hashed_password="",
            role=settings.default_role,
            is_verified=True,
        )
        db.add(user)
        await db.flush()
    return issue_tokens(user)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
async def update_user_profile(db: AsyncSession, user: User, data: UserProfileUpdate) -> User:
    """Update a user's profile fields."""
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.preferences is not None:
        user.preferences = data.preferences
    await db.flush()
    return user


async def list_users(db: AsyncSession, *, limit: int = 50, offset: int = 0) -> list[User]:
    """List users (admin)."""
    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(limit).offset(offset))
    return list(result.scalars().all())


async def set_user_active(db: AsyncSession, user_id: str, active: bool) -> User:
    """Activate/deactivate a user (admin)."""
    from fastapi import HTTPException, status

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = active
    await db.flush()
    return user


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------
async def create_workspace(db: AsyncSession, owner: User, data: WorkspaceCreate) -> Workspace:
    """Create a workspace owned by the given user (who becomes a member)."""
    ws = Workspace(
        name=data.name,
        description=data.description or "",
        owner_id=owner.id,
        is_shared_kb=data.is_shared_kb,
    )
    db.add(ws)
    await db.flush()
    membership = WorkspaceMembership(workspace_id=ws.id, user_id=owner.id, role="owner")
    db.add(membership)
    await db.flush()
    return ws


async def list_user_workspaces(db: AsyncSession, user: User) -> list[Workspace]:
    """List workspaces a user belongs to (owned or member)."""
    stmt = (
        select(Workspace)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
        .where(WorkspaceMembership.user_id == user.id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_workspace(db: AsyncSession, workspace_id: str) -> Workspace | None:
    """Fetch a workspace by id."""
    return await db.get(Workspace, workspace_id)


async def add_workspace_member(
    db: AsyncSession, workspace: Workspace, user_id: str, role: str = "member"
) -> WorkspaceMembership:
    """Add a user to a workspace (idempotent on role)."""
    from fastapi import HTTPException, status

    result = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace.id,
            WorkspaceMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        membership = WorkspaceMembership(
            workspace_id=workspace.id, user_id=user_id, role=role
        )
        db.add(membership)
        await db.flush()
    else:
        membership.role = role
        await db.flush()
    return membership


async def remove_workspace_member(db: AsyncSession, workspace_id: str, user_id: str) -> None:
    """Remove a user from a workspace."""
    from fastapi import HTTPException, status

    result = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    await db.delete(membership)


async def list_workspace_members(db: AsyncSession, workspace: Workspace) -> list[tuple[str, str, str]]:
    """Return (user_id, role, username) for workspace members."""
    stmt = (
        select(WorkspaceMembership.role, User.id, User.username)
        .join(User, User.id == WorkspaceMembership.user_id)
        .where(WorkspaceMembership.workspace_id == workspace.id)
    )
    result = await db.execute(stmt)
    return [(row[1], row[0], row[2]) for row in result.all()]


async def user_workspace_role(db: AsyncSession, user_id: str, workspace_id: str) -> str | None:
    """Return the user's role in a workspace, if any."""
    result = await db.execute(
        select(WorkspaceMembership.role).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
    )
    row = result.first()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------
async def create_conversation(
    db: AsyncSession, user: User, title: str | None, workspace_id: str | None
) -> Conversation:
    """Create a conversation owned by the user."""
    conv = Conversation(
        user_id=user.id,
        workspace_id=workspace_id,
        title=title or "New conversation",
    )
    db.add(conv)
    await db.flush()
    return conv


async def list_conversations(
    db: AsyncSession, user: User, workspace_id: str | None = None
) -> list[Conversation]:
    """List the user's conversations (optionally within a workspace)."""
    stmt = select(Conversation).where(Conversation.user_id == user.id)
    if workspace_id is not None:
        stmt = stmt.where(Conversation.workspace_id == workspace_id)
    stmt = stmt.order_by(Conversation.updated_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_owned_conversation(
    db: AsyncSession, user: User, conversation_id: str
) -> Conversation:
    """Fetch a conversation the user owns (or is a workspace member of)."""
    from fastapi import HTTPException, status

    conv = await db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conv.user_id == user.id:
        return conv
    role = await user_workspace_role(db, user.id, conv.workspace_id) if conv.workspace_id else None
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return conv


async def add_message(db: AsyncSession, conversation: Conversation, data: MessageCreate) -> Message:
    """Append a message to a conversation and bump its updated timestamp."""
    message = Message(
        conversation_id=conversation.id,
        role=data.role,
        content=data.content,
        citations=data.citations or {},
        correlation_id=data.correlation_id,
        token_count=data.token_count,
    )
    db.add(message)
    conversation.updated_at = datetime.utcnow()
    await db.flush()
    return message


async def rename_conversation(db: AsyncSession, conversation: Conversation, title: str) -> None:
    """Rename a conversation."""
    conversation.title = title
    await db.flush()


async def delete_conversation(db: AsyncSession, conversation: Conversation) -> None:
    """Delete a conversation and its messages (cascade)."""
    await db.delete(conversation)


async def search_conversations(
    db: AsyncSession, user: User, query: str
) -> list[Conversation]:
    """Search the user's conversations by title or message content."""
    q = f"%{query.lower()}%"
    stmt = (
        select(Conversation)
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user.id)
        .where(or_(Conversation.title.ilike(q), Message.content.ilike(q)))
        .distinct()
        .order_by(Conversation.updated_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------
async def record_audit(
    db: AsyncSession,
    *,
    action: str,
    user: User | None = None,
    request: Any = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """Append an audit/activity record (no-op when disabled)."""
    if not settings.audit_enabled:
        return
    ip = None
    ua = None
    if request is not None:
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")
    record = AuditLog(
        user_id=user.id if user else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip,
        user_agent=ua,
        meta=meta or {},
    )
    db.add(record)
    await db.flush()


async def list_audit(
    db: AsyncSession, *, limit: int = 50, offset: int = 0, user_id: str | None = None
) -> list[AuditLog]:
    """List audit records (admin), newest first."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def compute_stats(db: AsyncSession) -> dict[str, int]:
    """Compute platform usage statistics for the admin dashboard."""
    users = await db.execute(select(func.count()).select_from(User))
    active = await db.execute(select(func.count()).select_from(User).where(User.is_active.is_(True)))
    workspaces = await db.execute(select(func.count()).select_from(Workspace))
    conversations = await db.execute(select(func.count()).select_from(Conversation))
    messages = await db.execute(select(func.count()).select_from(Message))
    recent = await db.execute(select(func.count()).select_from(AuditLog))
    return {
        "total_users": users.scalar_one(),
        "active_users": active.scalar_one(),
        "total_workspaces": workspaces.scalar_one(),
        "total_conversations": conversations.scalar_one(),
        "total_messages": messages.scalar_one(),
        "recent_audit_count": recent.scalar_one(),
    }
