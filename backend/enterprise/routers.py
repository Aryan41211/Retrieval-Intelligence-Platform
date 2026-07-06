"""
Enterprise API routers: authentication, users, workspaces, conversations and
administration. All routers are included under the API prefix by the app.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.enterprise import security, services
from backend.enterprise.database import get_db
from backend.enterprise.exporters import export_conversation
from backend.enterprise.models import Conversation, Message, User, Workspace
from backend.enterprise.rbac import (
    get_current_active_user,
    require_permissions,
    require_roles,
)
from backend.enterprise.schemas import (
    AdminStats,
    AuditLogPublic,
    ConversationCreate,
    ConversationPublic,
    EmailVerificationRequest,
    MessageCreate,
    MessagePublic,
    OAuthStartResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserProfileUpdate,
    UserPublic,
    WorkspaceCreate,
    WorkspaceMemberAdd,
    WorkspaceMemberPublic,
    WorkspacePublic,
    ConversationDetailPublic,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])
workspaces_router = APIRouter(prefix="/workspaces", tags=["workspaces"])
conversations_router = APIRouter(prefix="/conversations", tags=["conversations"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@auth_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    user = await services.register_user(db, data)
    await services.record_audit(
        db, action="user.register", user=user, request=request, resource_type="user", resource_id=user.id
    )
    return services.issue_tokens(user)


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    user = await services.authenticate_user(db, data.identifier, data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    user.last_login_at = __import__("datetime").datetime.utcnow()
    await services.record_audit(db, action="user.login", user=user, request=request)
    return services.issue_tokens(user)


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await services.refresh_tokens(db, data.refresh_token)


@auth_router.post("/logout")
async def logout() -> dict[str, str]:
    """Stateless logout: clients should discard tokens."""
    return {"detail": "logged out"}


@auth_router.post("/password-reset/request")
async def password_reset_request(
    data: PasswordResetRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    await services.request_password_reset(db, data.email)
    return {"detail": "If the account exists, a reset link has been sent"}


@auth_router.post("/password-reset/confirm")
async def password_reset_confirm(
    data: PasswordResetConfirm, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    await services.reset_password(db, data.token, data.new_password)
    return {"detail": "password updated"}


@auth_router.post("/email/verify")
async def email_verify(
    data: EmailVerificationRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    await services.verify_email(db, data.token)
    return {"detail": "email verified"}


@auth_router.get("/oauth/{provider}/login", response_model=OAuthStartResponse)
async def oauth_login_start(provider: str) -> OAuthStartResponse:
    from backend.enterprise.oauth import get_authorization_url, is_oauth_configured

    if not is_oauth_configured(provider):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="OAuth provider not configured"
        )
    state = security.generate_oauth_state()
    return OAuthStartResponse(
        authorization_url=get_authorization_url(provider, state), state=state
    )


@auth_router.get("/oauth/{provider}/callback", response_model=TokenResponse)
async def oauth_callback(
    provider: str, code: str, state: str | None = None, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    return await services.oauth_login(db, provider, code)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
@users_router.get("/me", response_model=UserPublic)
async def get_me(current_user: User = Depends(get_current_active_user)) -> User:
    return current_user


@users_router.patch("/me", response_model=UserPublic)
async def update_me(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await services.update_user_profile(db, current_user, data)


@users_router.get("", response_model=list[UserPublic], dependencies=[Depends(require_permissions("manage_users"))])
async def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    return await services.list_users(db, limit=limit, offset=offset)


@users_router.post(
    "/{user_id}/deactivate",
    response_model=UserPublic,
    dependencies=[Depends(require_permissions("manage_users"))],
)
async def deactivate_user(user_id: str, db: AsyncSession = Depends(get_db)) -> User:
    return await services.set_user_active(db, user_id, active=False)


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------
async def _ensure_workspace_admin(db: AsyncSession, workspace_id: str, user: User) -> Workspace:
    ws = await services.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if ws.owner_id == user.id or user.role == "admin":
        return ws
    role = await services.user_workspace_role(db, user.id, workspace_id)
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return ws


@workspaces_router.post("", response_model=WorkspacePublic, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    return await services.create_workspace(db, current_user, data)


@workspaces_router.get("", response_model=list[WorkspacePublic])
async def my_workspaces(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[Workspace]:
    return await services.list_user_workspaces(db, current_user)


@workspaces_router.get("/shared", response_model=list[WorkspacePublic])
async def shared_knowledge_bases(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[Workspace]:
    from sqlalchemy import select

    result = await db.execute(select(Workspace).where(Workspace.is_shared_kb.is_(True)))
    return list(result.scalars().all())


@workspaces_router.get("/{workspace_id}", response_model=WorkspacePublic)
async def get_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    ws = await services.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    role = await services.user_workspace_role(db, current_user.id, workspace_id)
    if role is None and ws.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return ws


@workspaces_router.post("/{workspace_id}/members", response_model=WorkspaceMemberPublic)
async def add_member(
    workspace_id: str,
    data: WorkspaceMemberAdd,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceMemberPublic:
    ws = await _ensure_workspace_admin(db, workspace_id, current_user)
    member = await db.get(User, data.user_id)
    member_username = member.username if member else data.user_id
    membership = await services.add_workspace_member(db, ws, data.user_id, data.role)
    await services.record_audit(
        db,
        action="workspace.member_add",
        user=current_user,
        request=request,
        resource_type="workspace",
        resource_id=workspace_id,
    )
    return WorkspaceMemberPublic(
        user_id=membership.user_id, role=membership.role, username=member_username
    )


@workspaces_router.delete("/{workspace_id}/members/{user_id}")
async def remove_member(
    workspace_id: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await _ensure_workspace_admin(db, workspace_id, current_user)
    await services.remove_workspace_member(db, workspace_id, user_id)
    return {"detail": "member removed"}


@workspaces_router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberPublic])
async def list_members(
    workspace_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[WorkspaceMemberPublic]:
    ws = await services.get_workspace(db, workspace_id)
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    rows = await services.list_workspace_members(db, ws)
    return [WorkspaceMemberPublic(user_id=r[0], role=r[1], username=r[2]) for r in rows]


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------
@conversations_router.post("", response_model=ConversationPublic, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    return await services.create_conversation(db, current_user, data.title, data.workspace_id)


@conversations_router.get("", response_model=list[ConversationPublic])
async def list_conversations(
    workspace_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[Conversation]:
    return await services.list_conversations(db, current_user, workspace_id=workspace_id)


@conversations_router.get("/search", response_model=list[ConversationPublic])
async def search_conversations(
    q: str = Query(min_length=1),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[Conversation]:
    return await services.search_conversations(db, current_user, q)


@conversations_router.get("/{conversation_id}", response_model=ConversationDetailPublic)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    return await services.get_owned_conversation(db, current_user, conversation_id)


@conversations_router.post("/{conversation_id}/messages", response_model=MessagePublic)
async def add_message(
    conversation_id: str,
    data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    conv = await services.get_owned_conversation(db, current_user, conversation_id)
    return await services.add_message(db, conv, data)


@conversations_router.patch("/{conversation_id}", response_model=ConversationPublic)
async def rename_conversation(
    conversation_id: str,
    data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    conv = await services.get_owned_conversation(db, current_user, conversation_id)
    await services.rename_conversation(db, conv, data.title or conv.title)
    return conv


@conversations_router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    conv = await services.get_owned_conversation(db, current_user, conversation_id)
    await services.delete_conversation(db, conv)
    return {"detail": "conversation deleted"}


@conversations_router.get("/{conversation_id}/export")
async def export_conversation_route(
    conversation_id: str,
    fmt: str = Query(default="json", pattern="^(json|markdown|pdf)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    conv = await services.get_owned_conversation(db, current_user, conversation_id)
    from sqlalchemy import select

    from backend.enterprise.models import Message

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    messages = list(result.scalars().all())
    content, media_type, filename = export_conversation(conv, messages, fmt)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------
@admin_router.get("/dashboard", response_model=AdminStats)
async def admin_dashboard(
    current_user: User = Depends(require_permissions("view_analytics")),
    db: AsyncSession = Depends(get_db),
) -> AdminStats:
    stats = await services.compute_stats(db)
    return AdminStats(**stats)


@admin_router.get("/audit", response_model=list[AuditLogPublic])
async def admin_audit(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permissions("view_analytics")),
    db: AsyncSession = Depends(get_db),
) -> list[AuditLogPublic]:
    return await services.list_audit(db, limit=limit, offset=offset)
