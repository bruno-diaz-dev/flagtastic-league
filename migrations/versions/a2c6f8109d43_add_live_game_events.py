"""Add auditable live match capture.

Revision ID: a2c6f8109d43
Revises: 9a12e8d4c6f0
"""
from alembic import op

revision = "a2c6f8109d43"
down_revision = "9a12e8d4c6f0"
branch_labels = None
depends_on = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS game_live_sessions (
    game_id INTEGER PRIMARY KEY REFERENCES games(id) ON DELETE CASCADE,
    state TEXT NOT NULL DEFAULT 'live' CHECK (state IN ('live', 'completed')),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    started_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    finished_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS game_live_events (
    id BIGSERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES game_live_sessions(game_id) ON DELETE CASCADE,
    client_id UUID NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('pass_complete', 'pass_incomplete', 'passing_touchdown', 'touchdown', 'extra_one', 'extra_two', 'safety', 'sack', 'flag', 'interception', 'attendance', 'note')),
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    player_id INTEGER REFERENCES players(id) ON DELETE SET NULL,
    receiver_id INTEGER REFERENCES players(id) ON DELETE SET NULL,
    player_label TEXT,
    receiver_label TEXT,
    period INTEGER NOT NULL CHECK (period BETWEEN 1 AND 10),
    minute INTEGER NOT NULL CHECK (minute BETWEEN 0 AND 200),
    second INTEGER NOT NULL CHECK (second BETWEEN 0 AND 59),
    note TEXT NOT NULL DEFAULT '' CHECK (char_length(note) <= 240),
    recorded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    voided_at TIMESTAMPTZ,
    voided_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    void_reason TEXT CHECK (char_length(void_reason) <= 160),
    UNIQUE (game_id, client_id)
);
CREATE INDEX IF NOT EXISTS game_live_events_game_order ON game_live_events(game_id, id);
ALTER TABLE game_live_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE game_live_events ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'game_live_sessions' AND policyname = 'live_server_only') THEN
        CREATE POLICY live_server_only ON game_live_sessions AS RESTRICTIVE FOR ALL TO PUBLIC USING (false) WITH CHECK (false);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'game_live_events' AND policyname = 'live_server_only') THEN
        CREATE POLICY live_server_only ON game_live_events AS RESTRICTIVE FOR ALL TO PUBLIC USING (false) WITH CHECK (false);
    END IF;
END $$;
"""


def upgrade():
    """Serve through FastAPI; explicitly deny direct Data API access."""
    op.execute(SCHEMA)


def downgrade():
    op.drop_table("game_live_events")
    op.drop_table("game_live_sessions")
