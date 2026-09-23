"""create initial schema

Revision ID: 89d0a417bea9
Revises: 
Create Date: 2026-09-16 19:15:16.459323

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89d0a417bea9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the schema that existed when Alembic was introduced."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'active'")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()")
        ),
        sa.UniqueConstraint(
            "email",
            name="users_email_key"
        ),
        sa.CheckConstraint(
            """
            role IN (
                'league_admin',
                'team_representative',
                'player'
            )
            """,
            name="users_role_check"
        ),
        sa.CheckConstraint(
            """
            status IN (
                'active',
                'inactive'
            )
            """,
            name="users_status_check"
        )
    )

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("branch", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'")
        ),
        sa.UniqueConstraint(
            "name",
            "branch",
            "category", 
            name="teams_name_branch_category_key"
        )
    )

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("curp", sa.Text(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "curp",
            name="players_curp_key"
        )
    )

    op.create_table(
        "team_players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column(
            "player_id",
            sa.Integer(),
            nullable=False
        ),
        sa.Column(
            "jersey_number",
            sa.Integer(),
            nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="team_players_team_id_fkey",
            ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name="team_players_player_id_fkey",
            ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "team_id",
            "player_id",
            name="team_players_team_id_player_id_key"
        ),
        sa.UniqueConstraint(
            "team_id",
            "jersey_number",
            name="team_players_team_id_jersey_number_key"
        )
    )

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("home_team_id", sa.Integer(), nullable=False),
        sa.Column("away_team_id", sa.Integer(), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column(
            "away_score",
            sa.Integer(),
            nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["home_team_id"],
            ["teams.id"],
            name="games_home_team_id_fkey",
            ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["away_team_id"],
            ["teams.id"],
            name="games_away_team_id_fkey",
            ondelete="CASCADE"
        )
    )

    op.create_table(
        "team_representatives",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False
        ),
        sa.Column(
            "team_id",
            sa.Integer(),
            nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="team_representatives_user_id_fkey",
            ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="team_representatives_team_id_fkey",
            ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "user_id",
            "team_id",
            name="team_representatives_user_id_team_id_key"
        )
    )


def downgrade() -> None:
    """Remove the initial schema in reverse dependency order."""
    op.drop_table("team_representatives")
    op.drop_table("games")
    op.drop_table("team_players")
    op.drop_table("players")
    op.drop_table("teams")
    op.drop_table("users")
