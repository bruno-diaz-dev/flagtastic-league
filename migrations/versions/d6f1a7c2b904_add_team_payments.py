"""add team payments

Revision ID: d6f1a7c2b904
Revises: c4e8f0321b65
Create Date: 2026-10-07 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "d6f1a7c2b904"
down_revision = "c4e8f0321b65"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "teams",
        sa.Column(
            "registration_fee_cents",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_check_constraint(
        "teams_registration_fee_cents_nonnegative",
        "teams",
        "registration_fee_cents >= 0",
    )
    op.create_table(
        "team_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("receiver_name", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("proof_filename", sa.Text(), nullable=True),
        sa.Column("proof_media_type", sa.Text(), nullable=True),
        sa.Column("proof_data", sa.LargeBinary(), nullable=True),
        sa.Column("recorded_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "amount_cents > 0",
            name="team_payments_amount_cents_positive",
        ),
        sa.CheckConstraint(
            "method IN ('cash', 'transfer')",
            name="team_payments_method_check",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="team_payments_team_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_user_id"],
            ["users.id"],
            name="team_payments_recorded_by_user_id_fkey",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_team_payments_team_id_received_at",
        "team_payments",
        ["team_id", "received_at"],
    )
    op.execute("ALTER TABLE team_payments ENABLE ROW LEVEL SECURITY")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flagtastic_app') THEN
                GRANT SELECT, INSERT ON team_payments TO flagtastic_app;
                GRANT USAGE, SELECT ON SEQUENCE team_payments_id_seq TO flagtastic_app;
                CREATE POLICY backend_payments ON team_payments
                    FOR ALL TO flagtastic_app USING (true) WITH CHECK (true);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_index("ix_team_payments_team_id_received_at", table_name="team_payments")
    op.drop_table("team_payments")
    op.drop_constraint(
        "teams_registration_fee_cents_nonnegative",
        "teams",
        type_="check",
    )
    op.drop_column("teams", "registration_fee_cents")
