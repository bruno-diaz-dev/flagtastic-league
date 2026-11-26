"""Pre-create playoff games so officials can be assigned before teams advance."""

from alembic import op
import sqlalchemy as sa


revision = "7a3c9e1d5b42"
down_revision = "4d9f2b7a1c63"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("games", "home_team_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("games", "away_team_id", existing_type=sa.Integer(), nullable=True)
    op.add_column("games", sa.Column("home_pending_label", sa.Text(), nullable=True))
    op.add_column("games", sa.Column("away_pending_label", sa.Text(), nullable=True))
    op.create_check_constraint(
        "games_bracket_participants_check",
        "games",
        "(home_team_id IS NOT NULL AND away_team_id IS NOT NULL AND home_pending_label IS NULL AND away_pending_label IS NULL) "
        "OR (home_team_id IS NULL AND away_team_id IS NULL AND home_pending_label IS NOT NULL AND away_pending_label IS NOT NULL)",
    )
    op.execute("""
        WITH created_games AS (
            INSERT INTO games (
                home_team_id, away_team_id, week, field_number, start_time,
                is_friendly, game_date, venue, home_pending_label, away_pending_label
            )
            SELECT NULL, NULL, slots.week, slots.field_number, slots.start_time,
                   false, slots.game_date, slots.venue,
                   slots.label || ' en espera de equipos',
                   slots.label || ' en espera de equipos'
            FROM game_bracket_slots AS slots
            WHERE slots.target_game_id IS NULL
            RETURNING id, week, field_number, start_time
        )
        UPDATE game_bracket_slots AS slots
        SET target_game_id = created_games.id
        FROM created_games
        WHERE slots.target_game_id IS NULL
          AND slots.week = created_games.week
          AND slots.field_number = created_games.field_number
          AND slots.start_time = created_games.start_time
    """)


def downgrade():
    op.drop_constraint("games_bracket_participants_check", "games", type_="check")
    op.drop_column("games", "away_pending_label")
    op.drop_column("games", "home_pending_label")
    op.alter_column("games", "away_team_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("games", "home_team_id", existing_type=sa.Integer(), nullable=False)
