"""Store passing points and thrown interceptions for the quarterback index."""

from alembic import op
import sqlalchemy as sa


revision = "c5e2a7f19d30"
down_revision = "7a3c9e1d5b42"
branch_labels = None
depends_on = None


def upgrade():
    # Existing rows get 0; reimporting the official workbooks fills real values.
    op.add_column(
        "player_week_stats",
        sa.Column("passing_points", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "player_week_stats",
        sa.Column("passes_intercepted", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "player_week_stats_quarterback_non_negative_check",
        "player_week_stats",
        "passing_points >= 0 AND passes_intercepted >= 0",
    )


def downgrade():
    op.drop_constraint(
        "player_week_stats_quarterback_non_negative_check",
        "player_week_stats",
        type_="check",
    )
    op.drop_column("player_week_stats", "passes_intercepted")
    op.drop_column("player_week_stats", "passing_points")
