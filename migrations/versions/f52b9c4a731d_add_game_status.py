"""add game status

Revision ID: f52b9c4a731d
Revises: e31a7c9d52f0
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f52b9c4a731d"
down_revision: Union[str, Sequence[str], None] = "e31a7c9d52f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "games",
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'scheduled'"),
        ),
    )
    op.create_check_constraint(
        "games_status_check",
        "games",
        "status IN ('scheduled', 'postponed', 'completed')",
    )
    op.execute(
        """
        UPDATE games
        SET status = 'completed'
        WHERE home_score IS NOT NULL AND away_score IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint("games_status_check", "games", type_="check")
    op.drop_column("games", "status")
