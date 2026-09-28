"""add password reset tokens

Revision ID: e31a7c9d52f0
Revises: d21f6a8c4b90
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e31a7c9d52f0"
down_revision: Union[str, Sequence[str], None] = "d21f6a8c4b90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store short-lived, single-use reset tokens as hashes."""
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="password_reset_tokens_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "token_hash", name="password_reset_tokens_token_hash_key"
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="password_reset_tokens_expiration_check",
        ),
        sa.CheckConstraint(
            "used_at IS NULL OR used_at >= created_at",
            name="password_reset_tokens_usage_check",
        ),
    )
    op.create_index(
        "ix_password_reset_tokens_user_id",
        "password_reset_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_password_reset_tokens_expires_at",
        "password_reset_tokens",
        ["expires_at"],
    )
    op.execute("ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flagtastic_app') THEN
                CREATE POLICY backend_full_access_password_reset_tokens
                    ON password_reset_tokens FOR ALL TO flagtastic_app
                    USING (true) WITH CHECK (true);
            END IF;
        END
        $$
    """)


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
