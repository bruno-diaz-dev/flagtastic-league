"""Store passing points and thrown interceptions for the quarterback index.

Idempotent so a schema applied first through the Supabase SQL editor
(docs/sql/add-quarterback-passing-stats.sql) stays compatible with a later
``alembic upgrade head``.
"""

from alembic import op


revision = "c5e2a7f19d30"
down_revision = "7a3c9e1d5b42"
branch_labels = None
depends_on = None


def upgrade():
    # Existing rows get 0; reimporting the official workbooks fills real values.
    op.execute("""
        ALTER TABLE player_week_stats
            ADD COLUMN IF NOT EXISTS passing_points INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS passes_intercepted INTEGER NOT NULL DEFAULT 0
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'player_week_stats_quarterback_non_negative_check'
            ) THEN
                ALTER TABLE player_week_stats
                    ADD CONSTRAINT player_week_stats_quarterback_non_negative_check
                    CHECK (passing_points >= 0 AND passes_intercepted >= 0);
            END IF;
        END $$
    """)


def downgrade():
    op.execute("""
        ALTER TABLE player_week_stats
            DROP CONSTRAINT IF EXISTS player_week_stats_quarterback_non_negative_check,
            DROP COLUMN IF EXISTS passes_intercepted,
            DROP COLUMN IF EXISTS passing_points
    """)
