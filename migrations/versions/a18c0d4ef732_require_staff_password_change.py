"""require staff password change

Revision ID: a18c0d4ef732
Revises: f0a9c417d201
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a18c0d4ef732"
down_revision: Union[str, Sequence[str], None] = "f0a9c417d201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password", sa.Boolean(), nullable=False,
            server_default=sa.text("false")
        )
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
