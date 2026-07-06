"""
Security primitives: password hashing, JWT issuance/verification, and token
helpers for password reset / email verification / OAuth state.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from backend.enterprise.config import get_enterprise_settings
from backend.enterprise.rbac import permissions_for_role

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return _pwd_context.verify(password, password_hash)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(*, subject: str, role: str, expires_in: int | None = None) -> str:
    """Create a signed JWT access token carrying role and permissions."""
    settings = get_enterprise_settings()
    ttl = expires_in or settings.access_token_ttl_seconds
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "role": role,
        "permissions": permissions_for_role(role),
        "iat": _utcnow(),
        "exp": _utcnow() + timedelta(seconds=ttl),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(*, subject: str, expires_in: int | None = None) -> str:
    """Create a signed JWT refresh token (stateless)."""
    settings = get_enterprise_settings()
    ttl = expires_in or settings.refresh_token_ttl_seconds
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "refresh",
        "jti": uuid.uuid4().hex,
        "iat": _utcnow(),
        "exp": _utcnow() + timedelta(seconds=ttl),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """Decode and validate a JWT, asserting its type.

    Raises:
        jwt.PyJWTError: if the token is invalid, expired, or wrong type.
    """
    settings = get_enterprise_settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"expected {expected_type} token")
    return payload


def hash_token(token: str) -> str:
    """Return a SHA-256 hash of a bearer token for safe storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_oauth_state() -> str:
    """Generate a CSRF-protected OAuth state value."""
    return secrets.token_urlsafe(32)
