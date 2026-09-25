"""store profile photos in postgres

Revision ID: e15c3a7b942f
Revises: d04b7e8c31aa
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e15c3a7b942f"
down_revision: Union[str, Sequence[str], None] = "d04b7e8c31aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add persistent image bytes for serverless deployments."""
    op.add_column("players", sa.Column("profile_photo_data", sa.LargeBinary()))
    op.add_column("players", sa.Column("profile_photo_type", sa.Text()))


def downgrade() -> None:
    op.drop_column("players", "profile_photo_type")
    op.drop_column("players", "profile_photo_data")
