"""Unit tests for role-based access control (roles and permissions)."""

from backend.enterprise.rbac import (
    Permission,
    Role,
    permissions_for_role,
)


def test_admin_has_all_permissions() -> None:
    perms = set(permissions_for_role(Role.ADMIN.value))
    assert perms == {p.value for p in Permission}


def test_member_has_expected_permissions() -> None:
    perms = set(permissions_for_role(Role.MEMBER.value))
    assert Permission.CREATE_CONVERSATION.value in perms
    assert Permission.EXPORT_DATA.value in perms
    assert Permission.DELETE_CONVERSATION.value in perms
    assert Permission.MANAGE_USERS.value not in perms
    assert Permission.MANAGE_SYSTEM.value not in perms


def test_viewer_has_minimal_permissions() -> None:
    perms = set(permissions_for_role(Role.VIEWER.value))
    assert perms == {Permission.USE_SHARED_KB.value}


def test_unknown_role_falls_back_to_viewer() -> None:
    assert permissions_for_role("does-not-exist") == permissions_for_role(Role.VIEWER.value)


def test_roles_are_distinct_values() -> None:
    values = {Role.ADMIN.value, Role.MEMBER.value, Role.VIEWER.value}
    assert len(values) == 3
