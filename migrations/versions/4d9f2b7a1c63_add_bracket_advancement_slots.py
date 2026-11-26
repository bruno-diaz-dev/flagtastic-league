"""Store unresolved final and third-place schedule slots."""

from alembic import op
import sqlalchemy as sa


revision = "4d9f2b7a1c63"
down_revision = "0b8d2f4a6c90"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "game_bracket_slots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("field_number", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=True),
        sa.Column("venue", sa.Text(), nullable=True),
        sa.Column("branch", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("bracket_tier", sa.Text(), nullable=True),
        sa.Column("placement", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("source_game_id", sa.Integer(), nullable=False),
        sa.Column("opponent_game_id", sa.Integer(), nullable=False),
        sa.Column("target_game_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["source_game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opponent_game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_game_id"], ["games.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("week", "field_number", "start_time", name="game_bracket_slots_calendar_key"),
        sa.CheckConstraint("placement IN ('final', 'third')", name="game_bracket_slots_placement_check"),
        sa.CheckConstraint("bracket_tier IS NULL OR bracket_tier IN ('golden', 'silver')", name="game_bracket_slots_tier_check"),
    )
    op.execute('ALTER TABLE "game_bracket_slots" ENABLE ROW LEVEL SECURITY')
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='flagtastic_app') THEN
            CREATE POLICY backend_full_access_game_bracket_slots
            ON game_bracket_slots FOR ALL TO flagtastic_app
            USING (true) WITH CHECK (true);
          END IF;
        END $$
    """)


def downgrade():
    op.execute("DROP POLICY IF EXISTS backend_full_access_game_bracket_slots ON game_bracket_slots")
    op.drop_table("game_bracket_slots")
