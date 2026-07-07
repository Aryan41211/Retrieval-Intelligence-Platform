"""
Role-based access control and authentication dependencies.

Defines the role/permission model and the FastAPI dependencies used to protect
enterprise endpoints: ``get_current_user``, ``require_roles`` and
``require_permissions``.
"""

from enum import Enum
from collections.abc import Awaitable, Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.enterprise.database import get_db
from backend.enterprise.models import User

_bearer = HTTPBearer(auto_error=False)


class Permission(str, Enum):
    """Discrete permissions granted to users."""

    MANAGE_USERS = "manage_users"
    MANAGE_WORKSPACES = "manage_workspaces"
    MANAGE_WORKSPACE_MEMBERS = "manage_workspace_members"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_SYSTEM = "manage_system"
    CREATE_CONVERSATION = "create_conversation"
    EXPORT_DATA = "export_data"
    USE_SHARED_KB = "use_shared_kb"
    DELETE_CONVERSATION = "delete_conversation"


class Role(str, Enum):
    """User roles."""

    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


ROLE_PERMISSIONS: dict[str, list[str]] = {
    Role.ADMIN: [p.value for p in Permission],
    Role.MEMBER: [
        Permission.CREATE_CONVERSATION.value,
        Permission.EXPORT_DATA.value,
        Permission.USE_SHARED_KB.value,
        Permission.DELETE_CONVERSATION.value,
    ],
    Role.VIEWER: [
        Permission.USE_SHARED_KB.value,
    ],
}


def permissions_for_role(role: str) -> list[str]:
    """Return the list of permission values granted to a role."""
    return ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS[Role.VIEWER])


def _unauthorized(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the current user from a Bearer access token."""
    if credentials is None or not credentials.credentials:
        raise _unauthorized()
    try:
        from backend.enterprise.security import decode_token

        payload = decode_token(credentials.credentials, "access")
    except jwt.PyJWTError:
        raise _unauthorized("Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise _unauthorized("Malformed token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise _unauthorized("User no longer exists")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the authenticated user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive account")
    return current_user


def require_roles(*roles: str) -> Callable[..., Awaitable[User]]:
    """Dependency factory enforcing one of the given roles."""

    async def _dep(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return current_user

    return _dep


def require_permissions(*permissions: str) -> Callable[..., Awaitable[User]]:
    """Dependency factory enforcing all of the given permissions."""

    required = set(permissions)

    async def _dep(current_user: User = Depends(get_current_active_user)) -> User:
        granted = set(permissions_for_role(current_user.role))
        if not required.issubset(granted):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing required permissions",
            )
        return current_user

    return _dep
