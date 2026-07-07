"""Integration tests for the persistent chat / conversations API."""

from .fixtures import auth_headers, register


def _token(client, email, username):
    return register(client, email=email, username=username)["access_token"]


def test_create_and_list_conversations(client):
    token = _token(client, "conv@example.com", "conv")
    h = auth_headers(token)
    created = client.post(
        "/api/v1/conversations", headers=h, json={"title": "First chat"}
    )
    assert created.status_code == 201
    conv_id = created.json()["id"]

    listing = client.get("/api/v1/conversations", headers=h)
    assert listing.status_code == 200
    assert any(c["id"] == conv_id for c in listing.json())


def test_add_messages_and_get_detail(client):
    token = _token(client, "msg@example.com", "msg")
    h = auth_headers(token)
    conv_id = client.post("/api/v1/conversations", headers=h, json={"title": "Chat"}).json()["id"]

    m1 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=h,
        json={"role": "user", "content": "What is RAG?"},
    )
    assert m1.status_code == 200
    m2 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=h,
        json={"role": "assistant", "content": "Retrieval-Augmented Generation.", "citations": {"src": "doc1"}},
    )
    assert m2.status_code == 200

    detail = client.get(f"/api/v1/conversations/{conv_id}", headers=h)
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert len(messages) == 2
    assert messages[1]["citations"] == {"src": "doc1"}


def test_rename_conversation(client):
    token = _token(client, "rename@example.com", "rename")
    h = auth_headers(token)
    conv_id = client.post("/api/v1/conversations", headers=h, json={"title": "Old"}).json()["id"]
    resp = client.patch(
        f"/api/v1/conversations/{conv_id}", headers=h, json={"title": "New Title"}
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


def test_search_conversations_by_content(client):
    token = _token(client, "search@example.com", "search")
    h = auth_headers(token)
    conv_id = client.post("/api/v1/conversations", headers=h, json={"title": "Topic"}).json()["id"]
    client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=h,
        json={"role": "user", "content": "zebra crossing question"},
    )
    found = client.get("/api/v1/conversations/search?q=zebra", headers=h)
    assert found.status_code == 200
    assert any(c["id"] == conv_id for c in found.json())

    missing = client.get("/api/v1/conversations/search?q=notpresent", headers=h)
    assert missing.json() == []


def test_delete_conversation(client, db_path):
    token = _token(client, "del@example.com", "del")
    h = auth_headers(token)
    conv_id = client.post("/api/v1/conversations", headers=h, json={"title": "ToDelete"}).json()["id"]
    resp = client.delete(f"/api/v1/conversations/{conv_id}", headers=h)
    assert resp.status_code == 200
    detail = client.get(f"/api/v1/conversations/{conv_id}", headers=h)
    assert detail.status_code == 404


def test_export_formats(client):
    token = _token(client, "export@example.com", "export")
    h = auth_headers(token)
    conv_id = client.post("/api/v1/conversations", headers=h, json={"title": "Exportable"}).json()["id"]
    client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=h,
        json={"role": "user", "content": "hello"},
    )
    for fmt, ctype in [("json", "application/json"), ("markdown", "text/markdown"), ("pdf", "application/pdf")]:
        resp = client.get(f"/api/v1/conversations/{conv_id}/export?fmt={fmt}", headers=h)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith(ctype)
        assert "attachment" in resp.headers["content-disposition"]


def test_cannot_access_other_users_conversation(client):
    owner_token = _token(client, "ownerx@example.com", "ownerx")
    other_token = _token(client, "otherx@example.com", "otherx")
    conv_id = client.post(
        "/api/v1/conversations",
        headers=auth_headers(owner_token),
        json={"title": "Private"},
    ).json()["id"]
    resp = client.get(
        f"/api/v1/conversations/{conv_id}", headers=auth_headers(other_token)
    )
    assert resp.status_code in (403, 404)
