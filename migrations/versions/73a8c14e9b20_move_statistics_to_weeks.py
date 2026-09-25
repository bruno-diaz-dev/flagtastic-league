"""Move player statistics from games to complete weeks.

Revision ID: 73a8c14e9b20
Revises: 6d35f29c0e14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "73a8c14e9b20"
down_revision: Union[str, Sequence[str], None] = "6d35f29c0e14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _statistics_columns():
    """Return the shared metric columns for upgrade and downgrade tables."""
    return [
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("receptions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("interceptions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sacks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tackles", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passes_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passes_attempted", sa.Integer(), nullable=False, server_default="0")
    ]


def upgrade() -> None:
    """Aggregate existing game rows into one row per player, team and week."""
    op.create_table(
        "player_week_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("week", sa.Integer(), nullable=False),
        *_statistics_columns(),
        sa.ForeignKeyConstraint(
            ["player_id"], ["players.id"],
            name="player_week_stats_player_id_fkey", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"],
            name="player_week_stats_team_id_fkey", ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "week", "player_id", "team_id",
            name="player_week_stats_week_player_team_key"
        ),
        sa.CheckConstraint("week > 0", name="player_week_stats_week_check"),
        sa.CheckConstraint(
            "points >= 0 AND receptions >= 0 AND interceptions >= 0 "
            "AND sacks >= 0 AND tackles >= 0",
            name="player_week_stats_non_negative_check"
        ),
        sa.CheckConstraint(
            "passes_completed >= 0 AND passes_attempted >= 0 "
            "AND passes_completed <= passes_attempted",
            name="player_week_stats_passing_check"
        )
    )
    op.execute(
        """
        INSERT INTO player_week_stats (
            week, player_id, team_id, points, receptions, interceptions,
            sacks, tackles, passes_completed, passes_attempted
        )
        SELECT games.week, stats.player_id, stats.team_id,
               SUM(stats.points), SUM(stats.receptions),
               SUM(stats.interceptions), SUM(stats.sacks), SUM(stats.tackles),
               SUM(stats.passes_completed), SUM(stats.passes_attempted)
        FROM player_game_stats AS stats
        JOIN games ON games.id = stats.game_id
        GROUP BY games.week, stats.player_id, stats.team_id
        """
    )
    op.create_index("ix_player_week_stats_week", "player_week_stats", ["week"])
    op.create_index(
        "ix_player_week_stats_player_id", "player_week_stats", ["player_id"]
    )
    op.drop_table("player_game_stats")


def downgrade() -> None:
    """Restore weekly totals against one matching game for older code."""
    op.create_table(
        "player_game_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), nullable=False),
        *_statistics_columns(),
        sa.ForeignKeyConstraint(
            ["game_id"], ["games.id"],
            name="player_game_stats_game_id_fkey", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["player_id"], ["players.id"],
            name="player_game_stats_player_id_fkey", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"],
            name="player_game_stats_team_id_fkey", ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "game_id", "player_id",
            name="player_game_stats_game_id_player_id_key"
        ),
        sa.CheckConstraint(
            "points >= 0 AND receptions >= 0 AND interceptions >= 0 "
            "AND sacks >= 0 AND tackles >= 0",
            name="player_game_stats_non_negative_check"
        ),
        sa.CheckConstraint(
            "passes_completed >= 0 AND passes_attempted >= 0 "
            "AND passes_completed <= passes_attempted",
            name="player_game_stats_passing_check"
        )
    )
    op.execute(
        """
        INSERT INTO player_game_stats (
            game_id, player_id, team_id, points, receptions, interceptions,
            sacks, tackles, passes_completed, passes_attempted
        )
        SELECT matching_game.id, stats.player_id, stats.team_id,
               stats.points, stats.receptions, stats.interceptions,
               stats.sacks, stats.tackles,
               stats.passes_completed, stats.passes_attempted
        FROM player_week_stats AS stats
        JOIN LATERAL (
            SELECT games.id
            FROM games
            WHERE games.week = stats.week
              AND stats.team_id IN (games.home_team_id, games.away_team_id)
            ORDER BY games.id
            LIMIT 1
        ) AS matching_game ON TRUE
        """
    )
    op.create_index(
        "ix_player_game_stats_game_id", "player_game_stats", ["game_id"]
    )
    op.create_index(
        "ix_player_game_stats_player_id", "player_game_stats", ["player_id"]
    )
    op.drop_table("player_week_stats")
