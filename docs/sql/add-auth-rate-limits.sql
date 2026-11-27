-- Authentication rate-limit counters (equivalent to Alembic migration e8c1f5a3b7d2).
-- Run once in the Supabase SQL editor as the database owner: Preview first,
-- then Production, and only then merge the code that uses this table.
-- Idempotent and additive: it only creates a new table, with Row Level
-- Security enabled, and a later `alembic upgrade head` remains compatible.
-- Do not edit alembic_version.
BEGIN;

CREATE TABLE IF NOT EXISTS public.auth_rate_limits (
    bucket TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    PRIMARY KEY (bucket, key_hash, window_start)
);

CREATE INDEX IF NOT EXISTS auth_rate_limits_window_start_idx
    ON public.auth_rate_limits (window_start);

ALTER TABLE public.auth_rate_limits ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flagtastic_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON public.auth_rate_limits TO flagtastic_app;
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE schemaname = 'public' AND tablename = 'auth_rate_limits'
              AND policyname = 'backend_full_access_auth_rate_limits'
        ) THEN
            CREATE POLICY backend_full_access_auth_rate_limits
                ON public.auth_rate_limits FOR ALL TO flagtastic_app
                USING (true) WITH CHECK (true);
        END IF;
    END IF;
END $$;

COMMIT;

-- Verification: expect one row with rls_enabled = true.
SELECT relname, relrowsecurity AS rls_enabled
FROM pg_class
WHERE oid = 'public.auth_rate_limits'::regclass;

-- Verification: the backend role can use the table
-- (returns no rows when the role does not exist in this project).
SELECT has_table_privilege('flagtastic_app', 'public.auth_rate_limits',
                           'SELECT, INSERT, UPDATE, DELETE') AS backend_access
WHERE EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flagtastic_app');
