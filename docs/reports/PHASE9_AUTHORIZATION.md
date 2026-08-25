# Phase 9 Authorization — Role-Based Access Control

## Overview

RIP uses **RBAC with scope-based permissions**. Every authenticated user has a
role. Roles grant permissions (scopes). Permissions are checked at the router
boundary via the `require_permission` dependency.

## Roles

| Role | Default Permissions | Intended For |
|------|---------------------|--------------|
| `admin` | All permissions | Platform administrators |
| `member` | Create/export/delete own resources | Regular users |
| `viewer` | Read-only on shared knowledge bases | Read-only consumers |

## Permission Scopes

| Scope | Admin | Member | Viewer |
|-------|-------|--------|--------|
| `manage_users` | ✅ | — | — |
| `view_analytics` | ✅ | — | — |
| `manage_workspaces` | ✅ | — | — |
| `create_conversation` | ✅ | ✅ | — |
| `export_conversation` | ✅ | ✅ | — |
| `delete_conversation` | ✅ | ✅ | — |

## How It Works

1. JWT middleware decodes the access token and attaches the user identity to
   `request.state`.
2. The `require_permission` dependency resolves the user's role from the
   database and checks the required permission scope.
3. Unknown roles degrade safely to `viewer` (fail-closed).
4. Audit logs are appended for every mutating action.

## Enforcement Points

- Router-level: `require_permission("manage_users")`
- Service-level: optional injection for cross-cutting checks
- All enterprise routers (except auth) require authentication
