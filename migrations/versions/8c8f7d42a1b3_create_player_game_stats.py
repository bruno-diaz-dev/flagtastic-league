"""Create per-game player statistics.

Revision ID: 8c8f7d42a1b3
Revises: 155aeea5e3da
Create Date: 2026-09-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8c8f7d42a1b3"
down_revision: Union[str, Sequence[str], None] = "155aeea5e3da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the source-of-truth rows used for player totals."""
    op.create_table(
        "player_game_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("touchdowns", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("interceptions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sacks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("flag_pulls", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            name="player_game_stats_game_id_fkey",
            ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name="player_game_stats_player_id_fkey",
            ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="player_game_stats_team_id_fkey",
            ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "game_id",
            "player_id",
            name="player_game_stats_game_id_player_id_key"
        ),
        sa.CheckConstraint(
            "touchdowns >= 0 AND interceptions >= 0 "
            "AND sacks >= 0 AND flag_pulls >= 0",
            name="player_game_stats_non_negative_check"
        )
    )
    op.create_index(
        "ix_player_game_stats_game_id",
        "player_game_stats",
        ["game_id"]
    )
    op.create_index(
        "ix_player_game_stats_player_id",
        "player_game_stats",
        ["player_id"]
    )


def downgrade() -> None:
    """Remove per-game player statistics."""
    op.drop_table("player_game_stats")
