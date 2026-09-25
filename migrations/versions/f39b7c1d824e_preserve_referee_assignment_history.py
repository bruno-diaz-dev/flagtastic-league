"""preserve referee assignments when an assigning admin is removed

Revision ID: f39b7c1d824e
Revises: e27a54b69310
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f39b7c1d824e"
down_revision: Union[str, Sequence[str], None] = "e27a54b69310"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "game_referees_assigned_by_fkey", "game_referees", type_="foreignkey"
    )
    op.alter_column("game_referees", "assigned_by", nullable=True)
    op.create_foreign_key(
        "game_referees_assigned_by_fkey",
        "game_referees",
        "users",
        ["assigned_by"],
        ["id"],
        ondelete="SET NULL"
    )


def downgrade() -> None:
    # Rows without an assigning account cannot satisfy the previous contract.
    op.execute("DELETE FROM game_referees WHERE assigned_by IS NULL")
    op.drop_constraint(
        "game_referees_assigned_by_fkey", "game_referees", type_="foreignkey"
    )
    op.alter_column("game_referees", "assigned_by", nullable=False)
    op.create_foreign_key(
        "game_referees_assigned_by_fkey",
        "game_referees",
        "users",
        ["assigned_by"],
        ["id"],
        ondelete="RESTRICT"
    )
