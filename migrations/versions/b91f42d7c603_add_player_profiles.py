"""add player profile fields

Revision ID: b91f42d7c603
Revises: 73a8c14e9b20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b91f42d7c603"
down_revision: Union[str, Sequence[str], None] = "73a8c14e9b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing imported players remain valid while new account registrations
    # enforce a profile photo at the HTTP boundary.
    op.add_column("players", sa.Column("aka", sa.Text(), nullable=True))
    op.add_column(
        "players",
        sa.Column("profile_photo_path", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("players", "profile_photo_path")
    op.drop_column("players", "aka")
