"""add positions to game official assignments

Revision ID: a62c31d890bf
Revises: f39b7c1d824e
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a62c31d890bf"
down_revision: Union[str, Sequence[str], None] = "f39b7c1d824e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "game_referees",
        sa.Column("position", sa.Text(), nullable=True)
    )

    # Preserve older assignments by distributing them across the available
    # officiating positions in their original assignment order.
    op.execute(
        """
        WITH ranked AS (
            SELECT game_id, user_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY game_id ORDER BY assigned_at, user_id
                   ) AS position_number
            FROM game_referees
        )
        UPDATE game_referees AS assignment
        SET position = CASE ranked.position_number
            WHEN 1 THEN 'referee'
            WHEN 2 THEN 'down_judge'
            WHEN 3 THEN 'field_judge'
            WHEN 4 THEN 'side_judge'
            ELSE 'statistician'
        END
        FROM ranked
        WHERE assignment.game_id = ranked.game_id
          AND assignment.user_id = ranked.user_id
        """
    )
    op.alter_column("game_referees", "position", nullable=False)
    op.create_check_constraint(
        "game_referees_position_check",
        "game_referees",
        "position IN ('referee', 'down_judge', 'field_judge', 'side_judge', 'statistician')"
    )
    op.create_unique_constraint(
        "game_referees_game_id_position_key",
        "game_referees",
        ["game_id", "position"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "game_referees_game_id_position_key", "game_referees", type_="unique"
    )
    op.drop_constraint(
        "game_referees_position_check", "game_referees", type_="check"
    )
    op.drop_column("game_referees", "position")
