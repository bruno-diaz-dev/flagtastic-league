"""Decouple attendance check-ins from live capture sessions."""
from alembic import op

revision = "f7a4c9052b18"
down_revision = "e6a1f0472d89"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TABLE public.game_live_events DROP CONSTRAINT game_live_events_game_id_fkey;
ALTER TABLE public.game_live_events ADD CONSTRAINT game_live_events_game_id_fkey
FOREIGN KEY (game_id) REFERENCES public.games(id) ON DELETE CASCADE;
"""

def upgrade():
    op.execute(SCHEMA)

def downgrade():
    # Attendance may exist before a live session; retain it by refusing a lossy downgrade.
    op.execute("""
    DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM game_live_events e
                   LEFT JOIN game_live_sessions s ON s.game_id=e.game_id
                   WHERE s.game_id IS NULL) THEN
            RAISE EXCEPTION 'Attendance without live sessions must be preserved';
        END IF;
    END $$;
    ALTER TABLE public.game_live_events DROP CONSTRAINT game_live_events_game_id_fkey;
    ALTER TABLE public.game_live_events ADD CONSTRAINT game_live_events_game_id_fkey
    FOREIGN KEY (game_id) REFERENCES public.game_live_sessions(game_id) ON DELETE CASCADE;
    """)
