"""Allow the existing restricted backend role to operate live capture.

Revision ID: b3d7e9210a54
Revises: a2c6f8109d43
"""
from alembic import op

revision = "b3d7e9210a54"
down_revision = "a2c6f8109d43"
branch_labels = None
depends_on = None

SCHEMA = """
DROP POLICY IF EXISTS live_server_only ON game_live_sessions;
DROP POLICY IF EXISTS live_server_only ON game_live_events;
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flagtastic_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON game_live_sessions, game_live_events TO flagtastic_app;
        GRANT USAGE, SELECT ON SEQUENCE game_live_events_id_seq TO flagtastic_app;
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'game_live_sessions' AND policyname = 'backend_live_sessions') THEN
            CREATE POLICY backend_live_sessions ON game_live_sessions FOR ALL TO flagtastic_app USING (true) WITH CHECK (true);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'game_live_events' AND policyname = 'backend_live_events') THEN
            CREATE POLICY backend_live_events ON game_live_events FOR ALL TO flagtastic_app USING (true) WITH CHECK (true);
        END IF;
    END IF;
END $$;
"""


def upgrade():
    """Keep browser roles denied; authorize only the established backend."""
    op.execute(SCHEMA)


def downgrade():
    op.execute("DROP POLICY IF EXISTS backend_live_sessions ON game_live_sessions")
    op.execute("DROP POLICY IF EXISTS backend_live_events ON game_live_events")
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flagtastic_app') THEN
            REVOKE ALL ON game_live_sessions, game_live_events FROM flagtastic_app;
            REVOKE ALL ON SEQUENCE game_live_events_id_seq FROM flagtastic_app;
        END IF;
    END $$;""")
