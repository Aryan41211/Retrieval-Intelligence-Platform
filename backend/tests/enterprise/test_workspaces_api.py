"""Integration tests for the workspace collaboration API."""

from .conftest import auth_headers, promote_user, query_all, query_one, register


def _register(client, email, username):
    return register(client, email=email, username=username)


def _my_id(client, token):
    return client.get("/api/v1/users/me", headers=auth_headers(token)).json()["id"]


def test_create_workspace_and_become_member(client, db_path):
    tokens = _register(client, "wsowner@example.com", "wsowner")
    resp = client.post(
        "/api/v1/workspaces",
        headers=auth_headers(tokens["access_token"]),
        json={"name": "Team A", "description": "x", "is_shared_kb": True},
    )
    assert resp.status_code == 201
    ws_id = resp.json()["id"]
    members = query_all(
        db_path,
        "SELECT * FROM enterprise_workspace_memberships WHERE workspace_id=?",
        (ws_id,),
    )
    assert len(members) == 1


def test_list_my_workspaces(client, db_path):
    tokens = _register(client, "wsmember@example.com", "wsmember")
    client.post(
        "/api/v1/workspaces",
        headers=auth_headers(tokens["access_token"]),
        json={"name": "WS1"},
    )
    resp = client.get("/api/v1/workspaces", headers=auth_headers(tokens["access_token"]))
    assert resp.status_code == 200
    assert any(w["name"] == "WS1" for w in resp.json())


def test_shared_knowledge_bases_listed(client, db_path):
    tokens = _register(client, "shared@example.com", "shared")
    client.post(
        "/api/v1/workspaces",
        headers=auth_headers(tokens["access_token"]),
        json={"name": "Shared KB", "is_shared_kb": True},
    )
    client.post(
        "/api/v1/workspaces",
        headers=auth_headers(tokens["access_token"]),
        json={"name": "Private WS", "is_shared_kb": False},
    )
    resp = client.get("/api/v1/workspaces/shared", headers=auth_headers(tokens["access_token"]))
    assert resp.status_code == 200
    names = {w["name"] for w in resp.json()}
    assert "Shared KB" in names
    assert "Private WS" not in names


def test_add_and_remove_member(client, db_path):
    owner = _register(client, "addowner@example.com", "addowner")
    member = _register(client, "addmember@example.com", "addmember")
    member_id = _my_id(client, member["access_token"])
    ws = client.post(
        "/api/v1/workspaces",
        headers=auth_headers(owner["access_token"]),
        json={"name": "Collab"},
    ).json()
    ws_id = ws["id"]

    add = client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        headers=auth_headers(owner["access_token"]),
        json={"user_id": member_id, "role": "member"},
    )
    assert add.status_code == 200
    assert add.json()["username"] == "addmember"

    members = client.get(
        f"/api/v1/workspaces/{ws_id}/members",
        headers=auth_headers(owner["access_token"]),
    )
    assert any(m["user_id"] == member_id for m in members.json())

    rem = client.delete(
        f"/api/v1/workspaces/{ws_id}/members/{member_id}",
        headers=auth_headers(owner["access_token"]),
    )
    assert rem.status_code == 200
    after = query_all(
        db_path,
        "SELECT * FROM enterprise_workspace_memberships WHERE workspace_id=? AND user_id=?",
        (ws_id, member_id),
    )
    assert after == []


def test_non_member_cannot_view_workspace(client, db_path):
    owner = _register(client, "viewerowner@example.com", "viewerowner")
    outsider = _register(client, "outsider@example.com", "outsider")
    ws_id = client.post(
        "/api/v1/workspaces",
        headers=auth_headers(owner["access_token"]),
        json={"name": "Secret"},
    ).json()["id"]
    resp = client.get(
        f"/api/v1/workspaces/{ws_id}",
        headers=auth_headers(outsider["access_token"]),
    )
    assert resp.status_code == 403


def test_get_missing_workspace_returns_404(client):
    tokens = _register(client, "miss@example.com", "miss")
    resp = client.get(
        "/api/v1/workspaces/does-not-exist",
        headers=auth_headers(tokens["access_token"]),
    )
    assert resp.status_code == 404
