"""
Pydantic schemas for enterprise API request/response validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class MessageRole(str, Enum):
    """Permitted message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class WorkspaceRole(str, Enum):
    """Permitted workspace membership roles."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# --- Auth -------------------------------------------------------------------
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=160)


class UserLogin(BaseModel):
    identifier: str = Field(min_length=1, max_length=320, description="Email or username")
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)


class EmailVerificationRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)


class OAuthStartResponse(BaseModel):
    authorization_url: str
    state: str


# --- Users ------------------------------------------------------------------
class UserPublic(BaseModel):
    id: str
    email: EmailStr
    username: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    preferences: dict[str, Any] | None = None


# --- Workspaces --------------------------------------------------------------
class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    is_shared_kb: bool = False


class WorkspacePublic(BaseModel):
    id: str
    name: str
    description: str
    owner_id: str
    is_shared_kb: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceMemberAdd(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)
    # Previously an unconstrained str, so any value could be stored as a role.
    role: WorkspaceRole = WorkspaceRole.MEMBER


class WorkspaceMemberPublic(BaseModel):
    user_id: str
    role: str
    username: str


# --- Conversations -----------------------------------------------------------
class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    workspace_id: str | None = Field(default=None, max_length=36)


class MessageCreate(BaseModel):
    role: MessageRole = MessageRole.USER
    content: str = Field(min_length=1, max_length=100_000)
    citations: dict[str, Any] | None = None
    correlation_id: str | None = Field(default=None, max_length=64)
    token_count: int = Field(default=0, ge=0, le=10_000_000)


class MessagePublic(BaseModel):
    id: str
    role: str
    content: str
    citations: dict[str, Any]
    correlation_id: str | None
    token_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationPublic(BaseModel):
    id: str
    user_id: str
    workspace_id: str | None
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailPublic(ConversationPublic):
    messages: list[MessagePublic] = []


# --- Audit ------------------------------------------------------------------
class AuditLogPublic(BaseModel):
    id: str
    user_id: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Admin -------------------------------------------------------------------
class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_workspaces: int
    total_conversations: int
    total_messages: int
    recent_audit_count: int
