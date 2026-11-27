"""Count authentication attempts per client and account for rate limiting.

Idempotent so a schema applied first through the Supabase SQL editor
(docs/sql/add-auth-rate-limits.sql) stays compatible with a later
``alembic upgrade head``.
"""

from alembic import op


revision = "e8c1f5a3b7d2"
down_revision = "c5e2a7f19d30"
branch_labels = None
depends_on = None


def upgrade():
    # Keys are SHA-256 hashes: neither IP addresses nor emails are stored.
    op.execute("""
        CREATE TABLE IF NOT EXISTS auth_rate_limits (
            bucket TEXT NOT NULL,
            key_hash TEXT NOT NULL,
            window_start TIMESTAMPTZ NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
            PRIMARY KEY (bucket, key_hash, window_start)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS auth_rate_limits_window_start_idx
            ON auth_rate_limits (window_start)
    """)
    op.execute("ALTER TABLE auth_rate_limits ENABLE ROW LEVEL SECURITY")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flagtastic_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON auth_rate_limits TO flagtastic_app;
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE schemaname = 'public' AND tablename = 'auth_rate_limits'
                      AND policyname = 'backend_full_access_auth_rate_limits'
                ) THEN
                    CREATE POLICY backend_full_access_auth_rate_limits
                        ON auth_rate_limits FOR ALL TO flagtastic_app
                        USING (true) WITH CHECK (true);
                END IF;
            END IF;
        END
        $$
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS auth_rate_limits")
