"""add player accounts, passing statistics and game weeks

Revision ID: 42b7a831d5f0
Revises: 8c8f7d42a1b3
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "42b7a831d5f0"
down_revision: Union[str, Sequence[str], None] = "8c8f7d42a1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("player_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "users_player_id_fkey", "users", "players", ["player_id"], ["id"],
        ondelete="SET NULL"
    )
    op.create_unique_constraint("users_player_id_key", "users", ["player_id"])

    op.add_column(
        "games",
        sa.Column("week", sa.Integer(), nullable=False, server_default="1")
    )
    op.create_check_constraint("games_week_check", "games", "week > 0")

    op.add_column(
        "player_game_stats",
        sa.Column("passes_completed", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "player_game_stats",
        sa.Column("passes_attempted", sa.Integer(), nullable=False, server_default="0")
    )
    op.create_check_constraint(
        "player_game_stats_passing_check",
        "player_game_stats",
        "passes_completed >= 0 AND passes_attempted >= 0 "
        "AND passes_completed <= passes_attempted"
    )


def downgrade() -> None:
    op.drop_constraint(
        "player_game_stats_passing_check", "player_game_stats", type_="check"
    )
    op.drop_column("player_game_stats", "passes_attempted")
    op.drop_column("player_game_stats", "passes_completed")
    op.drop_constraint("games_week_check", "games", type_="check")
    op.drop_column("games", "week")
    op.drop_constraint("users_player_id_key", "users", type_="unique")
    op.drop_constraint("users_player_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "player_id")
