"""add team logos

Revision ID: b41e8d92c6f0
Revises: a18c0d4ef732
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b41e8d92c6f0"
down_revision: Union[str, Sequence[str], None] = "a18c0d4ef732"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Store team logos in PostgreSQL so serverless instances share them."""
    op.add_column("teams", sa.Column("logo_data", sa.LargeBinary()))
    op.add_column("teams", sa.Column("logo_type", sa.Text()))


def downgrade() -> None:
    op.drop_column("teams", "logo_type")
    op.drop_column("teams", "logo_data")
