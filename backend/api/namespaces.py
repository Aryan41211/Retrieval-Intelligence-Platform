"""Knowledge-base namespacing.

Every document used to be written into a single process-wide index
(``rip-default``), so any authenticated user could retrieve any other user's
documents regardless of workspace membership. Documents are now partitioned into
namespaces, each backed by its own vector index:

* ``user_<user_id>``       - a user's private documents
* ``ws_<workspace_id>``    - a workspace's shared documents

A caller may read their own namespace plus every workspace they belong to, and
may write to their own namespace or to a workspace where they hold a writing
role. Namespace ids are used as filenames, so they are strictly validated.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.enterprise.models import User, Workspace, WorkspaceMembership

# Namespace ids become file names (``<id>.index``, ``<id>.meta.json``), so only
# characters that are safe on every supported filesystem are permitted.
_SAFE_NAMESPACE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

USER_PREFIX = "user_"
WORKSPACE_PREFIX = "ws_"

#: Workspace roles permitted to add documents to a shared knowledge base.
WRITER_ROLES = frozenset({"owner", "admin", "member"})


class NamespaceKind(str, Enum):
    """What a namespace belongs to."""

    USER = "user"
    WORKSPACE = "workspace"


@dataclass(frozen=True)
class Namespace:
    """A resolved, validated knowledge-base namespace."""

    kind: NamespaceKind
    owner_id: str
    index_id: str

    @property
    def label(self) -> str:
        """Human-readable identifier for API responses."""
        return f"{self.kind.value}:{self.owner_id}"


class NamespaceError(ValueError):
    """Raised when a namespace id is malformed."""


def _sanitize(raw: str) -> str:
    """Return ``raw`` if it is safe to use as a file name component.

    Args:
        raw: Candidate namespace id.

    Returns:
        The validated id.

    Raises:
        NamespaceError: If the id contains anything outside ``[A-Za-z0-9_-]``,
            which would allow path traversal via the index filename.
    """
    if not _SAFE_NAMESPACE.match(raw or ""):
        raise NamespaceError(f"Unsafe namespace identifier: {raw!r}")
    return raw


def _owner_slug(owner_id: str) -> str:
    """Validate an owner id and reduce it to its namespace slug.

    The id is checked *before* the prefix is applied: prefixing an empty or
    malformed id would otherwise yield a superficially valid namespace (``user_``)
    that every such caller would share.
    """
    slug = (owner_id or "").replace("-", "")
    if not slug:
        raise NamespaceError("Namespace owner id must not be empty")
    return _sanitize(slug)


def user_namespace(user_id: str) -> Namespace:
    """Return the private namespace for a user."""
    index_id = _sanitize(f"{USER_PREFIX}{_owner_slug(user_id)}")
    return Namespace(kind=NamespaceKind.USER, owner_id=user_id, index_id=index_id)


def workspace_namespace(workspace_id: str) -> Namespace:
    """Return the shared namespace for a workspace."""
    index_id = _sanitize(f"{WORKSPACE_PREFIX}{_owner_slug(workspace_id)}")
    return Namespace(kind=NamespaceKind.WORKSPACE, owner_id=workspace_id, index_id=index_id)


async def _member_workspace_ids(db: AsyncSession, user: User) -> list[str]:
    """Return ids of every workspace the user belongs to."""
    result = await db.execute(
        select(WorkspaceMembership.workspace_id).where(WorkspaceMembership.user_id == user.id)
    )
    return [row[0] for row in result.all()]


async def readable_namespaces(db: AsyncSession, user: User) -> list[Namespace]:
    """Return every namespace the user is allowed to retrieve from.

    That is their own private namespace plus each workspace they are a member
    of. Ordering is stable: private namespace first, then workspaces by id.

    Args:
        db: Active database session.
        user: The authenticated caller.

    Returns:
        Namespaces to search, never empty (always includes the user's own).
    """
    namespaces = [user_namespace(user.id)]
    for workspace_id in sorted(await _member_workspace_ids(db, user)):
        namespaces.append(workspace_namespace(workspace_id))
    return namespaces


async def writable_namespace(
    db: AsyncSession,
    user: User,
    workspace_id: str | None,
) -> Namespace:
    """Resolve the namespace a document should be written to.

    Args:
        db: Active database session.
        user: The authenticated caller.
        workspace_id: Target workspace, or ``None`` for the caller's private
            knowledge base.

    Returns:
        The namespace to ingest into.

    Raises:
        PermissionError: If the caller may not write to the given workspace.
        LookupError: If the workspace does not exist.
    """
    if workspace_id is None:
        return user_namespace(user.id)

    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise LookupError(f"Workspace {workspace_id} not found")

    # Platform admins and the workspace owner can always write.
    if user.role == "admin" or workspace.owner_id == user.id:
        return workspace_namespace(workspace_id)

    result = await db.execute(
        select(WorkspaceMembership.role).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user.id,
        )
    )
    row = result.first()
    if row is None or row[0] not in WRITER_ROLES:
        raise PermissionError("You do not have permission to add documents to this workspace")
    return workspace_namespace(workspace_id)
