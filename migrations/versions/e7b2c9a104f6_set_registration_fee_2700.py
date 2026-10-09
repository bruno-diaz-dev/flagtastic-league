"""Set the league registration fee to 2700 pesos per team."""

from alembic import op
import sqlalchemy as sa


revision = "e7b2c9a104f6"
down_revision = "d6f1a7c2b904"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "teams", "registration_fee_cents",
        existing_type=sa.Integer(), server_default="270000",
    )
    op.execute("UPDATE teams SET registration_fee_cents = 270000")


def downgrade() -> None:
    op.alter_column(
        "teams", "registration_fee_cents",
        existing_type=sa.Integer(), server_default="0",
    )
