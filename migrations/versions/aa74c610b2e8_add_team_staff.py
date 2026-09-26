"""add team staff

Revision ID: aa74c610b2e8
Revises: b41e8d92c6f0
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "aa74c610b2e8"
down_revision: Union[str, Sequence[str], None] = "b41e8d92c6f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add optional staff names so existing teams remain valid."""
    op.add_column("teams", sa.Column("head_coach", sa.Text(), nullable=True))
    op.add_column("teams", sa.Column("coach", sa.Text(), nullable=True))
    op.add_column("teams", sa.Column("manager", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove roster staff metadata."""
    op.drop_column("teams", "manager")
    op.drop_column("teams", "coach")
    op.drop_column("teams", "head_coach")
