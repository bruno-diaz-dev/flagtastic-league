"""Add optional calendar dates and venues without inferring historical dates."""

from alembic import op

revision = "0b8d2f4a6c90"
down_revision = "f7a4c9052b18"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TABLE public.games ADD COLUMN IF NOT EXISTS game_date DATE;
ALTER TABLE public.games ADD COLUMN IF NOT EXISTS venue TEXT;
CREATE INDEX IF NOT EXISTS ix_games_calendar_slot
    ON public.games (week, game_date, field_number, start_time);
"""


def upgrade():
    op.execute(SCHEMA)


def downgrade():
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM public.games WHERE game_date IS NOT NULL OR venue IS NOT NULL) THEN
            RAISE EXCEPTION 'Recorded calendar dates and venues prevent a lossy downgrade';
        END IF;
    END $$;
    DROP INDEX IF EXISTS public.ix_games_calendar_slot;
    ALTER TABLE public.games DROP COLUMN venue;
    ALTER TABLE public.games DROP COLUMN game_date;
    """)
