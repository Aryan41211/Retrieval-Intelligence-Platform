"""Shared helpers for enterprise API tests (sync DB writes/reads)."""

import sqlite3
import time
from datetime import datetime, timedelta, timezone

from backend.enterprise import security


def create_token_row(
    db_path: str, table: str, user_id: str, raw_token: str, ttl: int = 3600
) -> None:
    """Insert a password-reset / email-verification token row directly."""
    expires = datetime.now(timezone.utc) + timedelta(seconds=ttl)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            f"INSERT INTO {table} (id, user_id, token_hash, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                f"tok-{int(time.time()*1000)}-{raw_token}",
                user_id,
                security.hash_token(raw_token),
                expires,
                datetime.now(timezone.utc),
            ),
        )
        conn.commit()
    finally:
        conn.close()
