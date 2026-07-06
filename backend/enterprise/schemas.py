"""
Pydantic schemas for enterprise API request/response validation.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


# --- Auth -------------------------------------------------------------------
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=160)


class UserLogin(BaseModel):
    identifier: str = Field(description="Email or username")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class EmailVerificationRequest(BaseModel):
    token: str


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
    user_id: str
    role: str = "member"


class WorkspaceMemberPublic(BaseModel):
    user_id: str
    role: str
    username: str


# --- Conversations -----------------------------------------------------------
class ConversationCreate(BaseModel):
    title: str | None = None
    workspace_id: str | None = None


class MessageCreate(BaseModel):
    role: str = "user"
    content: str
    citations: dict[str, Any] | None = None
    correlation_id: str | None = None
    token_count: int = 0


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
    messages: list[MessagePublic] = []

    model_config = {"from_attributes": True}


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
