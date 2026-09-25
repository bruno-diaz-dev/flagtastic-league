"""add multiple roles and referee assignments

Revision ID: c84d91f2a730
Revises: b91f42d7c603
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c84d91f2a730"
down_revision: Union[str, Sequence[str], None] = "b91f42d7c603"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep the legacy primary-role column compatible while callers migrate to
    # the cumulative user_roles relation.
    op.drop_constraint("users_role_check", "users", type_="check")
    op.create_check_constraint(
        "users_role_check",
        "users",
        "role IN ('league_admin', 'team_representative', 'player', 'referee')"
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="user_roles_user_id_fkey", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "role", name="user_roles_pkey"),
        sa.CheckConstraint(
            "role IN ('league_admin', 'team_representative', 'player', 'referee')",
            name="user_roles_role_check"
        )
    )
    op.execute(
        "INSERT INTO user_roles (user_id, role) SELECT id, role FROM users"
    )
    # Accounts promoted from player to administrator retain their player access.
    op.execute(
        """
        INSERT INTO user_roles (user_id, role)
        SELECT id, 'player' FROM users WHERE player_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )

    op.create_table(
        "game_referees",
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by", sa.Integer(), nullable=False),
        sa.Column(
            "assigned_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("NOW()")
        ),
        sa.ForeignKeyConstraint(
            ["game_id"], ["games.id"],
            name="game_referees_game_id_fkey", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="game_referees_user_id_fkey", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by"], ["users.id"],
            name="game_referees_assigned_by_fkey", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("game_id", "user_id", name="game_referees_pkey")
    )
    op.create_index("ix_game_referees_user_id", "game_referees", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_game_referees_user_id", table_name="game_referees")
    op.drop_table("game_referees")
    op.drop_table("user_roles")
    # Referee-only accounts cannot be represented by the previous schema.
    op.execute(
        "UPDATE users SET role = 'team_representative' WHERE role = 'referee'"
    )
    op.drop_constraint("users_role_check", "users", type_="check")
    op.create_check_constraint(
        "users_role_check",
        "users",
        "role IN ('league_admin', 'team_representative', 'player')"
    )
