# Playoff advancement

Finals and third-place games are created before their teams are known, so
officials can be assigned and the schedule published in advance. Teams are
filled in automatically once the semifinals are decided.

## Importing bracket slots

The XLSX calendar importer (`services/game_schedule_import.py`) treats a cell
whose local label contains `Final`, `3ro` or `Tercero` and whose visitor cell is
empty as a bracket slot. The label must name a category; `Fem`, `Var` or `Mix`
in the label restricts the branch. On confirmation (`POST
/api/games/schedule/confirm`, `repositories/games.py`):

1. The feeder semifinals are the same-category, non-friendly games of that
   jornada at the latest start time before the slot. Labels containing
   `Golden`/`Gold` or `Silver` split four or more feeders by field order: the
   first half feeds Golden, the second half Silver (seeds 1–4 and 5–8 in the
   league's bracket). A plain U12 label with three feeders uses the first two.
   If exactly two feeders cannot be determined, the whole confirmation is
   rejected with a conflict.
2. A row is stored in `game_bracket_slots` (jornada, field, time, date, venue,
   division, tier, `placement` = `final` or `third`, label, the two feeder game
   IDs and `target_game_id`). Re-importing the same jornada, field and time
   updates the slot instead of duplicating it.
3. If the slot has no target game yet, a game is created with no teams and
   both `home_pending_label` and `away_pending_label` set to
   `<label> en espera de equipos` (for example "Final U12 en espera de
   equipos"). A check constraint requires a game to have either both team IDs
   or both pending labels. Schedules, game details and referee views show the
   pending label in place of team names, and officials can be assigned to the
   game as usual.

## Automatic advancement

`services/bracket_advancement.py` runs whenever a feeder game's final score is
saved through the score endpoint or a live-capture finalization, and right
after a slot is imported. When both feeders are `completed` with non-tied
scores, the target game receives the two winners (final) or the two losers
(third place), ordered by the feeders' field number, and its pending labels
are cleared. Only a target game that still has no teams is filled; once teams
are set, later score corrections do not rewrite them.

## Effect on the regular season

The first jornada that holds any bracket slot marks the start of the playoffs.
That jornada and all later ones are excluded from the regular season used by
finals eligibility (`repositories/regular_season.py`), as are bracket target
games themselves. In the current season, jornada 7 holds the semifinals and
finals.
