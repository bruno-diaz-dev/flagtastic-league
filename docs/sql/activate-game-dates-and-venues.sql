-- Run once in the Supabase SQL editor as the database owner.
-- Existing games keep their IDs, scores, crew, and statistics.
BEGIN;
ALTER TABLE public.games ADD COLUMN IF NOT EXISTS game_date DATE;
ALTER TABLE public.games ADD COLUMN IF NOT EXISTS venue TEXT;
CREATE INDEX IF NOT EXISTS ix_games_calendar_slot
    ON public.games (week, game_date, field_number, start_time);
COMMIT;
