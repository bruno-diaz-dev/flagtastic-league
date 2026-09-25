"""add field number to games

Revision ID: e27a54b69310
Revises: c84d91f2a730
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e27a54b69310"
down_revision: Union[str, Sequence[str], None] = "c84d91f2a730"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Imported historical schedules may not identify a field. New games are
    # validated at the API boundary and referee-role imports complete this data.
    op.add_column("games", sa.Column("field_number", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "games_field_number_check",
        "games",
        "field_number IS NULL OR field_number BETWEEN 1 AND 8"
    )


def downgrade() -> None:
    op.drop_constraint("games_field_number_check", "games", type_="check")
    op.drop_column("games", "field_number")
