"""create sessions table

Revision ID: 155aeea5e3da
Revises: 89d0a417bea9
Create Date: 2026-09-22 21:19:56.356343

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '155aeea5e3da'
down_revision: Union[str, Sequence[str], None] = '89d0a417bea9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create revocable, expiring sessions without storing bearer tokens."""
    op.create_table("sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="sessions_user_id_fkey",
            ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "token_hash",
            name="sessions_token_hash_key"
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="sessions_expiration_check" 
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="sessions_revocation_check"
        )
    )

    op.create_index(
        "ix_sessions_user_id",
        "sessions",
        ["user_id"]
    )
    op.create_index(
        "ix_sessions_expires_at",
        "sessions",
        ["expires_at"]
    )


def downgrade() -> None:
    """Remove persistent session storage."""
    op.drop_table("sessions")
