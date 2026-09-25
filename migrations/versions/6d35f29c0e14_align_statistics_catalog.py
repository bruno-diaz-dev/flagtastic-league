"""align statistics with the league catalog

Revision ID: 6d35f29c0e14
Revises: 42b7a831d5f0
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6d35f29c0e14"
down_revision: Union[str, Sequence[str], None] = "42b7a831d5f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # These early V1 columns had placeholder names. Renaming preserves values
    # while aligning every layer with the league's official statistic names.
    op.alter_column("player_game_stats", "touchdowns", new_column_name="points")
    op.alter_column("player_game_stats", "flag_pulls", new_column_name="tackles")
    op.add_column(
        "player_game_stats",
        sa.Column("receptions", sa.Integer(), nullable=False, server_default="0")
    )
    op.drop_constraint(
        "player_game_stats_non_negative_check",
        "player_game_stats",
        type_="check"
    )
    op.create_check_constraint(
        "player_game_stats_non_negative_check",
        "player_game_stats",
        "points >= 0 AND receptions >= 0 AND interceptions >= 0 "
        "AND sacks >= 0 AND tackles >= 0"
    )


def downgrade() -> None:
    op.drop_constraint(
        "player_game_stats_non_negative_check",
        "player_game_stats",
        type_="check"
    )
    op.drop_column("player_game_stats", "receptions")
    op.alter_column("player_game_stats", "tackles", new_column_name="flag_pulls")
    op.alter_column("player_game_stats", "points", new_column_name="touchdowns")
    op.create_check_constraint(
        "player_game_stats_non_negative_check",
        "player_game_stats",
        "touchdowns >= 0 AND interceptions >= 0 "
        "AND sacks >= 0 AND flag_pulls >= 0"
    )
