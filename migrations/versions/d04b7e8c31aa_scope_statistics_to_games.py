"""scope statistics uniqueness to individual games

Revision ID: d04b7e8c31aa
Revises: c91f02a64b7e
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d04b7e8c31aa"
down_revision: Union[str, Sequence[str], None] = "c91f02a64b7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow one player row per game while retaining compact weekly imports."""
    op.drop_constraint(
        "player_week_stats_week_player_team_key",
        "player_week_stats",
        type_="unique"
    )
    op.create_index(
        "uq_player_game_stats_identity",
        "player_week_stats",
        ["game_id", "player_id", "team_id"],
        unique=True,
        postgresql_where=sa.text("game_id IS NOT NULL")
    )
    op.create_index(
        "uq_player_week_stats_unassigned_identity",
        "player_week_stats",
        ["week", "player_id", "team_id"],
        unique=True,
        postgresql_where=sa.text("game_id IS NULL")
    )


def downgrade() -> None:
    """Collapse multiple game rows back to the former weekly identity."""
    op.drop_index(
        "uq_player_week_stats_unassigned_identity",
        table_name="player_week_stats"
    )
    op.drop_index(
        "uq_player_game_stats_identity",
        table_name="player_week_stats"
    )
    op.execute(
        """
        WITH totals AS (
            SELECT MIN(id) AS kept_id, week, player_id, team_id,
                   SUM(points) AS points, SUM(receptions) AS receptions,
                   SUM(interceptions) AS interceptions, SUM(sacks) AS sacks,
                   SUM(tackles) AS tackles,
                   SUM(passes_completed) AS passes_completed,
                   SUM(passes_attempted) AS passes_attempted
            FROM player_week_stats
            GROUP BY week, player_id, team_id
        ), updated AS (
            UPDATE player_week_stats AS stats
            SET game_id = NULL, points = totals.points,
                receptions = totals.receptions,
                interceptions = totals.interceptions, sacks = totals.sacks,
                tackles = totals.tackles,
                passes_completed = totals.passes_completed,
                passes_attempted = totals.passes_attempted
            FROM totals WHERE stats.id = totals.kept_id
            RETURNING stats.id
        )
        DELETE FROM player_week_stats AS stats
        USING totals
        WHERE stats.week = totals.week
          AND stats.player_id = totals.player_id
          AND stats.team_id = totals.team_id
          AND stats.id <> totals.kept_id
        """
    )
    op.create_unique_constraint(
        "player_week_stats_week_player_team_key",
        "player_week_stats",
        ["week", "player_id", "team_id"]
    )
