"""Tenant isolation and file ingestion.

Every document used to land in one process-wide index, so any authenticated user
could retrieve any other user's documents. These tests pin the namespace model
that replaced it, and cover the multipart upload path that made the document
loaders reachable from the API.
"""

import io

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import reset_store_cache
from backend.api.namespaces import (
    NamespaceError,
    user_namespace,
    workspace_namespace,
)


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path, monkeypatch):
    """Give each test its own vector-store directory and a clean cache."""
    monkeypatch.setenv("VECTOR_STORE_STORAGE_DIR", str(tmp_path / "vs"))
    from backend.configs.settings import get_settings

    get_settings.cache_clear()
    reset_store_cache()
    yield
    reset_store_cache()
    get_settings.cache_clear()


def _register(client: TestClient, username: str) -> dict[str, str]:
    """Register a user and return an Authorization header."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "password": "correct-horse-battery",
        },
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _upload_text(client: TestClient, headers: dict, name: str, body: str, workspace_id=None):
    payload = {"filename": name, "content": body}
    if workspace_id:
        payload["workspace_id"] = workspace_id
    return client.post("/api/v1/documents/upload", json=payload, headers=headers)


class TestNamespaceIdentifiers:
    """Namespace ids become file names, so they must be strictly safe."""

    def test_user_namespace_is_filename_safe(self) -> None:
        ns = user_namespace("2f1c9e64-1c1e-4f0e-9a1a-3b7f5c8d9e01")
        assert ns.index_id == "user_2f1c9e641c1e4f0e9a1a3b7f5c8d9e01"
        assert "/" not in ns.index_id and "\\" not in ns.index_id

    def test_workspace_namespace_is_distinct_from_user(self) -> None:
        same_id = "2f1c9e641c1e4f0e9a1a3b7f5c8d9e01"
        assert user_namespace(same_id).index_id != workspace_namespace(same_id).index_id

    @pytest.mark.parametrize(
        "bad",
        ["../../etc/passwd", "a/b", "a\\b", "a b", "", "a" * 200],
    )
    def test_path_traversal_is_rejected(self, bad: str) -> None:
        with pytest.raises(NamespaceError):
            user_namespace(bad)


class TestTenantIsolation:
    """C1: one user's documents must never reach another user."""

    def test_user_cannot_retrieve_another_users_document(self, client: TestClient) -> None:
        alice = _register(client, "alice")
        bob = _register(client, "bob")

        secret = "Project Zephyr launches in November with a budget of 4 million euros."
        assert _upload_text(client, alice, "secret.txt", secret).status_code == 200

        # Alice finds her own document.
        own = client.post(
            "/api/v1/retrieval/search",
            json={"query": "Project Zephyr budget", "top_k": 5},
            headers=alice,
        )
        assert own.status_code == 200
        assert any("Zephyr" in r["content"] for r in own.json()["results"])

        # Bob must not.
        other = client.post(
            "/api/v1/retrieval/search",
            json={"query": "Project Zephyr budget", "top_k": 5},
            headers=bob,
        )
        assert other.status_code == 200
        assert other.json()["results"] == []

    def test_chat_is_not_grounded_in_another_tenants_documents(self, client: TestClient) -> None:
        alice = _register(client, "alice2")
        bob = _register(client, "bob2")
        _upload_text(client, alice, "secret.txt", "The launch codeword is Zephyr.")

        answer = client.post(
            "/api/v1/chat", json={"query": "What is the launch codeword?"}, headers=bob
        )
        assert answer.status_code == 200
        assert "Zephyr" not in answer.text

    def test_search_reports_the_namespaces_it_consulted(self, client: TestClient) -> None:
        alice = _register(client, "alice3")
        resp = client.post("/api/v1/retrieval/search", json={"query": "anything"}, headers=alice)
        assert resp.status_code == 200
        searched = resp.json()["namespaces_searched"]
        assert len(searched) == 1 and searched[0].startswith("user:")


class TestWorkspaceSharing:
    """Workspace members share a knowledge base; outsiders do not."""

    def test_member_can_read_documents_uploaded_to_a_workspace(self, client: TestClient) -> None:
        owner = _register(client, "wsowner3")
        member = _register(client, "wsmember3")
        outsider = _register(client, "wsoutsider3")

        member_id = client.get("/api/v1/users/me", headers=member).json()["id"]
        workspace_id = client.post(
            "/api/v1/workspaces", json={"name": "Team KB"}, headers=owner
        ).json()["id"]
        assert (
            client.post(
                f"/api/v1/workspaces/{workspace_id}/members",
                json={"user_id": member_id, "role": "member"},
                headers=owner,
            ).status_code
            == 200
        )

        shared = "The quarterly revenue target is 12 million dollars."
        upload = _upload_text(client, owner, "targets.txt", shared, workspace_id=workspace_id)
        assert upload.status_code == 200, upload.text
        assert upload.json()["namespace"] == f"workspace:{workspace_id}"

        found = client.post(
            "/api/v1/retrieval/search",
            json={"query": "quarterly revenue target", "top_k": 5},
            headers=member,
        )
        assert found.status_code == 200
        assert any("quarterly revenue" in r["content"] for r in found.json()["results"])

        denied = client.post(
            "/api/v1/retrieval/search",
            json={"query": "quarterly revenue target", "top_k": 5},
            headers=outsider,
        )
        assert denied.json()["results"] == []

    def test_outsider_cannot_upload_to_a_workspace(self, client: TestClient) -> None:
        owner = _register(client, "wsowner4")
        outsider = _register(client, "wsoutsider4")
        workspace_id = client.post(
            "/api/v1/workspaces", json={"name": "Closed KB"}, headers=owner
        ).json()["id"]

        resp = _upload_text(client, outsider, "x.txt", "should not land", workspace_id=workspace_id)
        assert resp.status_code == 403

    def test_unknown_workspace_is_404(self, client: TestClient) -> None:
        user = _register(client, "wsunknown")
        resp = _upload_text(client, user, "x.txt", "content", workspace_id="does-not-exist")
        assert resp.status_code == 404


class TestFileUpload:
    """C2: the loader package is reachable through a multipart endpoint."""

    def test_supported_formats_are_advertised(self, client: TestClient) -> None:
        headers = _register(client, "formats")
        resp = client.get("/api/v1/documents/supported-formats", headers=headers)
        assert resp.status_code == 200
        assert ".pdf" in resp.json()["extensions"]
        assert ".txt" in resp.json()["extensions"]

    def test_plain_text_file_is_ingested_and_retrievable(self, client: TestClient) -> None:
        headers = _register(client, "fileuser")
        content = b"Photosynthesis converts light energy into chemical energy in plants."

        resp = client.post(
            "/api/v1/documents/upload/file",
            files={"file": ("biology.txt", io.BytesIO(content), "text/plain")},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "ingested"
        assert body["filename"] == "biology.txt"
        assert body["chunks_indexed"] >= 1

        found = client.post(
            "/api/v1/retrieval/search",
            json={"query": "how do plants convert light", "top_k": 3},
            headers=headers,
        )
        assert any("Photosynthesis" in r["content"] for r in found.json()["results"])

    def test_markdown_file_is_ingested(self, client: TestClient) -> None:
        headers = _register(client, "mduser")
        content = b"# Notes\n\nThe capital of Japan is Tokyo.\n"
        resp = client.post(
            "/api/v1/documents/upload/file",
            files={"file": ("notes.md", io.BytesIO(content), "text/markdown")},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text

    def test_unsupported_extension_is_rejected(self, client: TestClient) -> None:
        headers = _register(client, "exeuser")
        resp = client.post(
            "/api/v1/documents/upload/file",
            files={"file": ("payload.exe", io.BytesIO(b"MZ\x00"), "application/octet-stream")},
            headers=headers,
        )
        assert resp.status_code == 415

    def test_empty_file_is_rejected(self, client: TestClient) -> None:
        headers = _register(client, "emptyfile")
        resp = client.post(
            "/api/v1/documents/upload/file",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_path_traversal_filename_is_neutralised(self, client: TestClient) -> None:
        """A directory component in the upload name must not escape the temp dir."""
        headers = _register(client, "traversal")
        resp = client.post(
            "/api/v1/documents/upload/file",
            files={
                "file": (
                    "../../evil.txt",
                    io.BytesIO(b"Traversal attempt content for indexing."),
                    "text/plain",
                )
            },
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["filename"] == "evil.txt"

    def test_file_upload_requires_authentication(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/documents/upload/file",
            files={"file": ("a.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert resp.status_code == 401


class TestDocumentRegistry:
    """Listing and deletion are derived from the vector store's own records."""

    def test_list_shows_only_the_callers_documents(self, client: TestClient) -> None:
        alice = _register(client, "listalice")
        bob = _register(client, "listbob")
        _upload_text(client, alice, "alice.txt", "Alice's private research notes on fungi.")

        mine = client.get("/api/v1/documents/list", headers=alice)
        assert mine.status_code == 200
        assert [d["filename"] for d in mine.json()] == ["alice.txt"]

        theirs = client.get("/api/v1/documents/list", headers=bob)
        assert theirs.status_code == 200
        assert theirs.json() == []

    def test_list_reports_chunk_counts_and_namespace(self, client: TestClient) -> None:
        headers = _register(client, "listcounts")
        _upload_text(client, headers, "long.txt", "Sentence about retrieval. " * 60)

        entries = client.get("/api/v1/documents/list", headers=headers).json()
        assert len(entries) == 1
        assert entries[0]["chunk_count"] >= 1
        assert entries[0]["namespace"].startswith("user:")

    def test_delete_removes_the_document_from_retrieval(self, client: TestClient) -> None:
        headers = _register(client, "deldoc")
        _upload_text(client, headers, "temp.txt", "Ephemeral content about volcanoes and lava.")

        listed = client.get("/api/v1/documents/list", headers=headers).json()
        document_id = listed[0]["document_id"]

        removed = client.delete(f"/api/v1/documents/{document_id}", headers=headers)
        assert removed.status_code == 200
        assert removed.json()["chunks_removed"] >= 1

        assert client.get("/api/v1/documents/list", headers=headers).json() == []

        found = client.post(
            "/api/v1/retrieval/search",
            json={"query": "volcanoes and lava", "top_k": 5},
            headers=headers,
        )
        assert all("Ephemeral" not in r["content"] for r in found.json()["results"])

    def test_deleting_an_unknown_document_is_404(self, client: TestClient) -> None:
        headers = _register(client, "delmissing")
        resp = client.delete("/api/v1/documents/does-not-exist", headers=headers)
        assert resp.status_code == 404
