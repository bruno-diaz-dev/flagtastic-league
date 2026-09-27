"""add active roster memberships

Revision ID: d8e8f4a9c201
Revises: aa74c610b2e8
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8e8f4a9c201"
down_revision: Union[str, Sequence[str], None] = "aa74c610b2e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Keep former members for history while freeing their jersey numbers."""
    op.add_column(
        "team_players",
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true())
    )
    op.drop_constraint(
        "team_players_team_id_jersey_number_key",
        "team_players",
        type_="unique"
    )
    op.create_index(
        "team_players_team_id_jersey_number_key",
        "team_players",
        ["team_id", "jersey_number"],
        unique=True,
        postgresql_where=sa.text("active")
    )
    # Calendar age is the age reached at any point during the current year.
    # Existing valid CURPs receive the same value as new registrations.
    op.execute(
        """
        UPDATE players
        SET age = EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER -
            CASE
                WHEN SUBSTRING(curp FROM 17 FOR 1) ~ '^[0-9]$'
                    THEN 1900 + SUBSTRING(curp FROM 5 FOR 2)::INTEGER
                ELSE 2000 + SUBSTRING(curp FROM 5 FOR 2)::INTEGER
            END
        WHERE curp ~ '^[A-Z]{4}[0-9]{6}[A-Z0-9]{6}[A-Z0-9][0-9]$'
          AND (
            CASE
                WHEN SUBSTRING(curp FROM 17 FOR 1) ~ '^[0-9]$'
                    THEN 1900 + SUBSTRING(curp FROM 5 FOR 2)::INTEGER
                ELSE 2000 + SUBSTRING(curp FROM 5 FOR 2)::INTEGER
            END
          ) <= EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER
        """
    )


def downgrade() -> None:
    """Restore the original all-membership jersey uniqueness constraint."""
    op.drop_index(
        "team_players_team_id_jersey_number_key",
        table_name="team_players"
    )
    # The former schema cannot represent inactive memberships. Dropping them
    # preserves its uniqueness rule without deleting player identities/stats.
    op.execute("DELETE FROM team_players WHERE NOT active")
    op.create_unique_constraint(
        "team_players_team_id_jersey_number_key",
        "team_players",
        ["team_id", "jersey_number"]
    )
    op.drop_column("team_players", "active")
