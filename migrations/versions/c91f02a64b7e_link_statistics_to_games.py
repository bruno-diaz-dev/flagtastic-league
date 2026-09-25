"""link player statistics to individual games

Revision ID: c91f02a64b7e
Revises: b73e4c9a102d
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c91f02a64b7e"
down_revision: Union[str, Sequence[str], None] = "b73e4c9a102d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "player_week_stats", sa.Column("game_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "player_week_stats_game_id_fkey",
        "player_week_stats", "games", ["game_id"], ["id"],
        ondelete="SET NULL"
    )
    op.create_index(
        "ix_player_week_stats_game_id", "player_week_stats", ["game_id"]
    )
    # Historical rows are safe to associate only when their team played one
    # unambiguous game in that jornada.
    op.execute(
        """
        UPDATE player_week_stats AS stats
        SET game_id = matched.game_id
        FROM (
            SELECT stats_row.id AS stats_id, MIN(games.id) AS game_id
            FROM player_week_stats AS stats_row
            JOIN games ON games.week = stats_row.week
              AND stats_row.team_id IN (games.home_team_id, games.away_team_id)
            GROUP BY stats_row.id
            HAVING COUNT(games.id) = 1
        ) AS matched
        WHERE stats.id = matched.stats_id
        """
    )


def downgrade() -> None:
    op.drop_index("ix_player_week_stats_game_id", table_name="player_week_stats")
    op.drop_constraint(
        "player_week_stats_game_id_fkey", "player_week_stats", type_="foreignkey"
    )
    op.drop_column("player_week_stats", "game_id")
