# Authorization Report — Phase 9

**Project:** Retrieval Intelligence Platform (RIP)
**Phase:** 9 — Enterprise Features
**Module:** `backend/enterprise/rbac.py`, `backend/enterprise/routers.py`

---

## 1. Summary

Authorization is enforced with **Role-Based Access Control (RBAC)**. A small,
explicit role→permission matrix drives FastAPI dependency factories that protect
every enterprise endpoint. Users authenticate via JWT (see Authentication
Report) and the resolved `User` carries their role; permissions are embedded in
the access token and re-derived from the role on each request.

## 2. Roles

Defined in `rbac.Role` (str-Enum):

| Role | Intended use |
|------|--------------|
| `admin` | Full platform control (all permissions). |
| `member` | Create conversations, export, use shared KBs, delete own conversations. |
| `viewer` | Read-only access to shared knowledge bases. |

The default role for new users is configurable (`ENTERPRISE_DEFAULT_ROLE`,
default `member`).

## 3. Permissions

Defined in `rbac.Permission` (str-Enum):

```
manage_users, manage_workspaces, manage_workspace_members, view_analytics,
manage_system, create_conversation, export_data, use_shared_kb,
delete_conversation
```

The matrix `ROLE_PERMISSIONS` maps each role to its granted permissions:

- **admin** → all permissions.
- **member** → `create_conversation`, `export_data`, `use_shared_kb`,
  `delete_conversation`.
- **viewer** → `use_shared_kb` only.
- **unknown role** → falls back to the viewer permission set (fail-closed).

`permissions_for_role(role)` is the single source of truth; it is also used when
minting the JWT so the token's `permissions` claim matches the role.

## 4. Enforcement Points

`rbac.py` exposes the FastAPI dependencies used throughout `routers.py`:

- `get_current_user` — resolves the `User` from the `Bearer` access token
  (HTTPBearer), validates the JWT, and loads the user from the DB.
- `get_current_active_user` — additionally rejects inactive accounts (`403`).
- `require_roles(*roles)` — allows the request only if the user's role is in
  the supplied set (`403` otherwise).
- `require_permissions(*permissions)` — allows the request only if the user's
  role grants **all** required permissions (`403` otherwise).

### Endpoint protection (examples)

| Endpoint(s) | Guard |
|-------------|-------|
| `/users/me`, `/conversations/*`, `/workspaces` (create/list) | `get_current_active_user` |
| `/users`, `/users/{id}/deactivate` | `require_permissions("manage_users")` |
| `/admin/dashboard`, `/admin/audit` | `require_permissions("view_analytics")` |
| Workspace member management | `_ensure_workspace_admin` (owner / admin / `owner`/`admin` workspace role) |

Workspace-scoped access is enforced both by the membership check and by
`services.get_owned_conversation`, which allows a user to read a conversation
they own **or** are a member of via the parent workspace (otherwise `403`/`404`).

## 5. Test Coverage

- **Unit** (`test_rbac.py`): admin has all permissions; member has the expected
  subset and lacks admin/system perms; viewer is minimal; unknown role falls
  back to viewer; roles are distinct.
- **API** (`test_users_api.py`): non-admin cannot list users (`403`); admin can
  list and deactivate users; profile read/update works.
- **API** (`test_admin_api.py`): non-admin cannot view the dashboard (`403`);
  admin can read dashboard stats and audit logs.
- **API** (`test_workspaces_api.py`): non-members cannot view a workspace
  (`403`); workspace admins can add/remove members.

**All authorization tests pass (part of the 65-test enterprise suite).**

## 6. Design Notes & Security Posture

- **Fail-closed:** missing/invalid tokens → `401`; insufficient role/permission
  → `403`. Unknown roles degrade to viewer permissions.
- **Single source of truth:** permissions are computed from the role, avoiding
  drift between the JWT claim and the DB.
- **No privilege escalation paths:** admin-only routes require explicit
  `manage_*` / `view_analytics` permissions; workspace membership changes
  require owner/admin authority.
- Token `permissions` are embedded for performance but always re-derived from
  the role server-side on each request via `get_current_user`.
