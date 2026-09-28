"""add referee profile photos

Revision ID: b6c4d91e7a20
Revises: d8e8f4a9c201
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6c4d91e7a20"
down_revision: Union[str, Sequence[str], None] = "d8e8f4a9c201"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store photos for operational accounts without player identities."""
    op.add_column("users", sa.Column("profile_photo_path", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("profile_photo_data", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("profile_photo_type", sa.Text(), nullable=True))
    op.create_unique_constraint(
        "users_profile_photo_path_key", "users", ["profile_photo_path"]
    )


def downgrade() -> None:
    op.drop_constraint("users_profile_photo_path_key", "users", type_="unique")
    op.drop_column("users", "profile_photo_type")
    op.drop_column("users", "profile_photo_data")
    op.drop_column("users", "profile_photo_path")
