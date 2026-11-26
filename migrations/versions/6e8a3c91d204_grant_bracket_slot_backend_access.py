"""Grant the backend role access to bracket advancement slots."""

from alembic import op


revision = "6e8a3c91d204"
down_revision = "4d9f2b7a1c63"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flagtastic_app') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE
              ON TABLE public.game_bracket_slots TO flagtastic_app;
            GRANT USAGE, SELECT, UPDATE
              ON SEQUENCE public.game_bracket_slots_id_seq TO flagtastic_app;
          END IF;
        END $$
    """)


def downgrade():
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flagtastic_app') THEN
            REVOKE ALL PRIVILEGES
              ON TABLE public.game_bracket_slots FROM flagtastic_app;
            REVOKE ALL PRIVILEGES
              ON SEQUENCE public.game_bracket_slots_id_seq FROM flagtastic_app;
          END IF;
        END $$
    """)
