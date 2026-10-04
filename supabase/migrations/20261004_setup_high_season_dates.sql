-- Extend the existing setup administrator permissions to the season dates.
-- Existing row-level security policies still restrict updates to administrators.
BEGIN;
GRANT UPDATE (start_season, end_season) ON public.high_season TO authenticated;
COMMIT;
