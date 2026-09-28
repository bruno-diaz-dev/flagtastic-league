"""add referee aka

Revision ID: c7a4d2e91f30
Revises: b6c4d91e7a20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7a4d2e91f30"
down_revision: Union[str, Sequence[str], None] = "b6c4d91e7a20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store the public AKA used by referee directory and schedule OCR."""
    op.add_column("users", sa.Column("aka", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "aka")
