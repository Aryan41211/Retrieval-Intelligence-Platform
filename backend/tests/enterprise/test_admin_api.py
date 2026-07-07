"""Integration tests for the administration API (dashboard, audit, analytics)."""

from .fixtures import auth_headers, promote_user, query_all, register


def _token(client, email, username):
    return register(client, email=email, username=username)["access_token"]


def test_admin_dashboard_returns_stats(client, db_path):
    admin = _token(client, "adminstat@example.com", "adminstat")
    promote_user(db_path, "adminstat@example.com", "admin")
    register(client, email="user1@example.com", username="user1")

    resp = client.get("/api/v1/admin/dashboard", headers=auth_headers(admin))
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_users"] >= 2
    assert "total_workspaces" in stats
    assert "total_conversations" in stats


def test_admin_audit_lists_records(client, db_path):
    admin = _token(client, "auditadmin@example.com", "auditadmin")
    promote_user(db_path, "auditadmin@example.com", "admin")
    register(client, email="audited@example.com", username="audited")

    resp = client.get("/api/v1/admin/audit", headers=auth_headers(admin))
    assert resp.status_code == 200
    assert any(a["action"] == "user.register" for a in resp.json())


def test_non_admin_cannot_view_dashboard(client):
    member = _token(client, "dashmember@example.com", "dashmember")
    resp = client.get("/api/v1/admin/dashboard", headers=auth_headers(member))
    assert resp.status_code == 403


def test_audit_log_persisted_on_registration(client, db_path):
    register(client, email="logged@example.com", username="logged")
    rows = query_all(
        db_path, "SELECT * FROM enterprise_audit_logs WHERE action=?", ("user.register",)
    )
    assert len(rows) >= 1
    assert rows[0]["resource_type"] == "user"
