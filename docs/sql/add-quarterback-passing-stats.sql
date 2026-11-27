-- Quarterback index columns (equivalent to Alembic migration c5e2a7f19d30).
-- Run once in the Supabase SQL editor as the database owner: Preview first,
-- then Production, and only then merge the code that reads these columns.
-- Idempotent and additive: existing rows get 0, nothing else is modified, and
-- a later `alembic upgrade head` remains compatible. Do not edit alembic_version.
BEGIN;

ALTER TABLE public.player_week_stats
    ADD COLUMN IF NOT EXISTS passing_points INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS passes_intercepted INTEGER NOT NULL DEFAULT 0;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'player_week_stats_quarterback_non_negative_check'
    ) THEN
        ALTER TABLE public.player_week_stats
            ADD CONSTRAINT player_week_stats_quarterback_non_negative_check
            CHECK (passing_points >= 0 AND passes_intercepted >= 0);
    END IF;
END $$;

COMMIT;

-- Verification: expect two rows, both INTEGER, NOT NULL, default 0.
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'player_week_stats'
  AND column_name IN ('passing_points', 'passes_intercepted')
ORDER BY column_name;

-- Verification: the backend role can read and write the new columns
-- (returns no rows when the role does not exist in this project).
SELECT column_name,
       has_column_privilege('flagtastic_app', 'public.player_week_stats',
                            column_name, 'SELECT, INSERT, UPDATE') AS backend_access
FROM (VALUES ('passing_points'), ('passes_intercepted')) AS columns(column_name)
WHERE EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flagtastic_app');
