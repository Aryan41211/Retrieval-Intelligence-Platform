"""Unit tests for security primitives (password hashing, JWT, tokens)."""

import jwt
import pytest

from backend.enterprise import security
from backend.enterprise.rbac import Role, permissions_for_role


def test_hash_password_is_bcrypt_and_verifiable() -> None:
    hashed = security.hash_password("sup3rsecret")
    assert hashed != "sup3rsecret"
    assert hashed.startswith("$2")
    assert security.verify_password("sup3rsecret", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = security.hash_password("sup3rsecret")
    assert security.verify_password("wrong", hashed) is False


def test_verify_password_handles_garbage_hash() -> None:
    assert security.verify_password("x", "not-a-hash") is False
    assert security.verify_password("x", "") is False


def test_access_token_roundtrip_carries_role_and_permissions() -> None:
    token = security.create_access_token(subject="user-1", role=Role.ADMIN.value)
    payload = security.decode_token(token, "access")
    assert payload["sub"] == "user-1"
    assert payload["role"] == Role.ADMIN.value
    assert set(payload["permissions"]) == set(permissions_for_role(Role.ADMIN.value))
    assert payload["type"] == "access"


def test_refresh_token_roundtrip() -> None:
    token = security.create_refresh_token(subject="user-2")
    payload = security.decode_token(token, "refresh")
    assert payload["sub"] == "user-2"
    assert payload["type"] == "refresh"
    assert "jti" in payload


def test_decode_token_rejects_wrong_type() -> None:
    access = security.create_access_token(subject="u", role=Role.MEMBER.value)
    with pytest.raises(jwt.PyJWTError):
        security.decode_token(access, "refresh")


def test_decode_token_rejects_tampered_token() -> None:
    token = security.create_access_token(subject="u", role=Role.MEMBER.value) + "x"
    with pytest.raises(jwt.PyJWTError):
        security.decode_token(token, "access")


def test_hash_token_is_deterministic_sha256() -> None:
    import hashlib

    assert security.hash_token("abc") == hashlib.sha256(b"abc").hexdigest()
    assert security.hash_token("abc") == security.hash_token("abc")


def test_generate_oauth_state_is_unique() -> None:
    assert security.generate_oauth_state() != security.generate_oauth_state()
