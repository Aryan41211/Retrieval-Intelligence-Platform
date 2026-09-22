"""add token_version to enterprise_users

Revision ID: 5f2c81ab7d01
Revises: 46eb3e5d3ecd
Create Date: 2026-09-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "5f2c81ab7d01"
down_revision: str | None = "46eb3e5d3ecd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "enterprise_users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("enterprise_users", "token_version")