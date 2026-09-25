"""add scheduled start time to games

Revision ID: b73e4c9a102d
Revises: a62c31d890bf
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b73e4c9a102d"
down_revision: Union[str, Sequence[str], None] = "a62c31d890bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("games", sa.Column("start_time", sa.Time(), nullable=True))


def downgrade() -> None:
    op.drop_column("games", "start_time")
