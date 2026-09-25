"""enable row level security

Revision ID: f0a9c417d201
Revises: e15c3a7b942f
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f0a9c417d201"
down_revision: Union[str, Sequence[str], None] = "e15c3a7b942f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = (
    "alembic_version", "sessions", "team_representatives", "team_players",
    "users", "user_roles", "game_referees", "player_week_stats", "games",
    "players", "teams"
)


def upgrade() -> None:
    """Block Data API access while permitting the private backend role."""
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flagtastic_app') THEN
                    EXECUTE 'CREATE POLICY backend_full_access_{table}
                        ON {table} FOR ALL TO flagtastic_app
                        USING (true) WITH CHECK (true)';
                END IF;
            END
            $$
        """)


def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f'DROP POLICY IF EXISTS backend_full_access_{table} ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
