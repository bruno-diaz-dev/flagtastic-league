# Statistics Upload

League administrators import the official statistics workbook from
`/statistics`. Three endpoints accept it; all require `league_admin`:

| Endpoint | Scope |
|---|---|
| `POST /api/statistics/import` | Every `Wk N` sheet in the workbook |
| `POST /api/weeks/{week}/player-stats/import` | One jornada |
| `POST /api/weeks/{week}/player-stats/import-division` | One jornada and one division; rejects files containing other divisions |

## What an import does and does not do

The game schedule is the source of truth for which games exist. A statistics
import only **links player statistics to games that are already registered**.
It never creates games, never writes or corrects scores, and never changes a
game's status. A source game that cannot be matched to a registered,
non-friendly game in the same jornada is skipped and reported.

Each 15-row team block is paired with the next block to form one source game.
Its two team labels are matched against the participants of the registered
games of that jornada. When the same pair of youth names exists in more than
one branch, an exact match against a completed game's published score is used
only to choose between registered games; it never writes the score.

Players are resolved from branch, category, team and jersey number; names in
the spreadsheet are not identities. Statistics are stored per player, team and
game in `player_week_stats`. Imports never delete a week's or a division's
existing statistics: they insert new player/game rows and, depending on the
**existing records** option, either keep (`preserve`, the page default) or
overwrite (`update`, the API default) rows that already exist for the same
player and game. The `Asistencia` row is also saved as attendance check-ins
for the linked game (see [Finals eligibility](#attendance-and-finals-eligibility)).

## Skipped records and warnings

Problems that only affect one record or one source game are skipped rather
than rejecting the file. Responses include `skipped`, `skipped_count`,
`warnings` and `preserved_weeks`. Current skip reasons:

| Reason | Meaning |
|---|---|
| `team_unresolved` | A team label does not match a registered team; that source game's records are skipped |
| `game_unresolved` | No single registered game matches the source pair |
| `game_team_unresolved` | A record belongs to a source game that was skipped because one of its teams or games could not be resolved |
| `jersey_number_not_found` | The jersey number is not on the resolved team's roster; no player is created and the stats are not given to anyone else |
| `unlinked_duplicate_retained` | An older row for the same player and jornada with no game link coexists with the row for this game; it is kept unchanged for review |

Warnings (the rest of the record still imports):

| Warning | Meaning |
|---|---|
| `interception_thrower_unresolved` | An `Intercepciones Pase` jersey did not pass in that game block, so the interception is not credited to any QB |
| `passing_points_thrower_unresolved` | A `6/2/1 Puntos` jersey did not pass in that game block, so the passing points are not credited |
| `incomplete_passing` | A QB has more completions than recorded attempts. Both passing counts are omitted for that player/game: an existing row keeps its stored values, a new row gets zero. No attempts are inferred. |

The page lists every skipped record and warning after the import and offers
them as a CSV download (`estadisticas-omitidas-<timestamp>.csv`). If no record
of a jornada can be resolved, that jornada is reported in `preserved_weeks` and
its stored data stays unchanged.

The following still reject the **whole** import (nothing is written):
malformed workbooks or values, an incomplete 15-row block, a block without a
rival, rivals from different divisions, the same player twice in one game, a
player/jornada with several stored rows that cannot be told apart, a
single-jornada file in which a player appears in several games without game
blocks, and any jornada where an included team has a game in live capture or
with live-captured plays (attendance alone does not block).

`GET /api/statistics/import-template` downloads the compact one-row-per-player
template (`rama`, `categoria`, `equipo`, `numero`, metric columns). It has no
game blocks, so it cannot distinguish two games of one player in a jornada.

## Upload size

Vercel limits Function request bodies to 4.5 MB, independently of the
server's 15 MiB workbook limit (`MAX_WORKBOOK_BYTES`). The browser therefore
prepares large files before sending them (`static/statistics_upload.js`):

- Originals up to **32 MiB** are accepted; larger files are rejected.
- Files of **4 MiB** or less are sent unchanged.
- Larger files are rebuilt in a Web Worker
  (`static/statistics_upload_worker.js`) with the vendored SheetJS CE 0.20.3
  (`static/vendor/xlsx-0.20.3.min.js`). Only `Wk` sheets are read (or the
  first sheet when there are none), only columns A:BA are exported, cached
  values are kept, interior blank rows are preserved for the 15-row block
  parser, and empty week templates are dropped. The original file is not
  modified.
- A prepared file above **4 MiB** is rejected before anything is sent.

A platform `413` produces a size error even when its body is plain text. The
progress bar shows real percentages for reading, preparing and uploading the
file, then fixed stages while the server processes it. The submit button stays
disabled until the request finishes.

## Workbook parsing notes

The parser ignores repeated `Equipo / Categoria / Estadistica` print headers
and unused week templates, and both the game and player readers share the same
block reader so a repeated header cannot shift game identities. Named game
pairs with no player events or attendance on either side are schedule
placeholders and are skipped, while later games keep their original block
index. Attendance-only records (including jersey zero) are retained.

Quarterback data: `Intentos Pase` gives attempts (completed passes included)
and `Para % Pases` gives completions. `6 Puntos`, `2 Puntos` and `1 Puntos`
credit passing points, and `Intercepciones Pase` credits thrown interceptions,
to the jersey only if that jersey passed in the same game block. Compact
templates without the optional `puntos_pase` / `intercepciones_lanzadas`
columns keep the stored quarterback values on update.

## Confirmed source identities

The league administrator confirmed these source corrections; they apply only
to the exact labels, jornadas and divisions listed in code:

- `Valkirias Blanco` is the workbook label for `Vikingos Blanco` in
  **femenil U14** (`services/team_matching.py`). Literal registered identities
  take precedence; missing or duplicate targets remain unresolved.
- Some source pairs are labeled with the wrong branch and are read as
  **femenil**: jornada 3 `Diablos Rojo–Lanceros` and `Diablos Amarillo–UCA`
  (U18) and `Diablos–Ravens` (libre), plus specific U14/U18 pairs in jornadas 4
  and 5 (`_CONFIRMED_SOURCE_BRANCHES` in `services/statistics_import.py`).

## Attendance and finals eligibility

Imported attendance is stored as `attendance` events in `game_live_events`
(note `Importada desde estadísticas`) and is counted by the finals-eligibility
report together with live check-ins. Repeated imports do not duplicate it.

## Testing

Run `node --test tests/js/statistics_upload.test.cjs` for transport
regressions and `node tests/browser/statistics_upload.cjs` (Playwright) for the
browser flow. Verify large official files in Preview. Never use a Production
import as a smoke test: `update` mode overwrites existing statistics.
