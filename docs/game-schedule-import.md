# Game schedule import

League administrators analyze an image, XLSX, or CSV and review the matched
games before confirming. Analysis never writes to the database. The browser
image reader targets the league's six-field matrix; manual entry, XLSX, and CSV
support fields 1 through 8.

For images, the browser locates the schedule grid, detects every horizontal
hour boundary, and splits each active field into local and visitor cells. This
keeps blank fields and lightly colored grid lines from shifting later games into
the wrong time slot. Team text and the time column are recognized separately.

Image recognition preserves irregular schedules. When the source is clearly an
hourly grid, minute noise such as `13:09` is normalized to the printed whole
hour, and a duplicated or missing hour is repaired only when its immediate
neighbors prove the sequence. Unreadable times remain empty in the review
cards. Administrators must fill the time for each selected game before
confirmation; recognized times can also be corrected. Recognition is not a
substitute for reviewing team matches and times before confirmation.

Failed block-OCR time cells receive a second, individual single-line OCR pass.
The review uses responsive cards with complete team names and divisions,
field, time, date and venue. Each card offers “Editar partido” for corrections;
its visible summary follows edits. There is no horizontal review table. The observed `Pitbulls Ir` glyph error resolves to `Pitbulls Jr` without
collapsing the distinct `Pitbulls Sr` team.

Confirmation is transactional. Repeated identical slots are skipped. Replacing
teams in a slot is allowed only when the existing game has no scores, linked
statistics or assigned officials. Conflicts return HTTP 409 and roll back the
entire batch. Duplicate slots in the same request are rejected. Imports are
serialized to prevent concurrent confirmations from creating the same slot.

Slot identity is week, field and start time. Moving a game to another slot is
not a rescheduling operation: it creates a new slot. To move an existing game,
administrators use the schedule board or the game's time/field editor. Both
update the same game ID through `PATCH /api/games/{id}/schedule`, retaining its
crew, statistics and live session. Completed/scored games and occupied target
slots in the same jornada are rejected. Postponed games keep that status.
The board supports drag/drop and keyboard/mobile form controls. No database
migration is required.

No database migration is required by these safeguards.

## Game lifecycle

Imported games begin as `scheduled`. Saving both scores marks a game
`completed`. A league administrator may postpone or restore an unplayed game,
or apply the same status change to every unplayed game in one jornada.
Postponed games reject score capture.

Administrators may also delete one game or a complete jornada after an explicit
confirmation. Referee assignments are removed with the game; historical weekly
statistics remain and their nullable game link is cleared. These controls are
for exceptional schedule changes, not routine rescheduling.

## Verification

- `pytest -q`: API, parser, authorization and persistence tests using the test DB.
- `node --test tests/js/*.test.cjs`: browser time-parsing regressions; also in CI.
- Preview smoke test: analyze the actual league image and verify the complete
  `11:00` through `21:00` grid, all 52 proposed games, and the distinct
  `Pitbulls Jr`/`Pitbulls Sr` matches. Inspect every proposal, confirm, then
  repeat and verify that no games are duplicated.

## Spreadsheet team recognition

XLSX/CSV recognition compares team names within the explicitly written division;
sharing age/branch suffixes never substitutes for name evidence. Unsupported ages
such as U7 remain unresolved instead of being guessed as U6/U8. Numeric `18` is
U18. Unified youth categories allow legacy branches, but an explicit branch can
distinguish duplicate names. In U12 spreadsheets, an omitted branch means mixto
(the league's confirmed source convention); explicit femenil remains femenil. The confirmed schedule alias `Lobos Inf` resolves to
`Lobos Kids`, distinct from adult `Lobos`.

Every parsed game remains in review, including unmatched games. Each side offers
a registered-team selector labelled with branch and category, retaining the
original file label for comparison. Choosing both compatible teams enables an
official game without creating guests. Mark a game friendly only when confirmed
as such; unresolved guest names and different divisions can then be reviewed.
Analysis never creates teams or confirms games automatically.

Friendlies may pair registered teams from different divisions without changing
those teams' categories. U7 is accepted for invited friendly participants only;
it does not add an official league registration category.

Referee-role imports identify the game by its slot first: jornada, field and
time (plus date and venue when present). Team names, resolved with the same
identity rules as game registration (including friendly guests), only confirm
it: a regular game needs both names to be the slot's teams, and playoff rows
such as "Final U12" bind to their slot before and after the semifinals resolve.
If the names point to a game at another slot, that game is proposed with a
"move" notice. Image grids narrow candidates to the cell's field and time.
Ambiguous games and unknown referees remain warnings; importing never creates
referee accounts.

Confirming a role assigns officials only. A game is moved to the role's field,
time, date or venue only when the administrator ticks **Mover el partido** for
that row (`apply_calendar_change`); the review shows the game's current slot.
Editing the field, date or venue of a row ticks it automatically.

The admin board includes five separate official selectors for the selected game:
Referee, Down Judge, Field Judge, Side Judge and Statistician. Each slot saves
independently using existing admin assignment endpoints; selecting “Sin asignar”
and saving removes that assignment. Existing crew values are loaded, duplicate
people are rejected, and “Actualizar lista” refreshes active referee accounts.
Stale crew responses cannot overwrite the editor after selecting another game.

## Friendly referee crews

The referee import review identifies friendlies from the stored game, for images
as well as XLSX/CSV. All five crew slots are optional on those games, including
Referee and Down Judge. Official games still require both core positions. The
server enforces this using the locked database row when confirming the batch,
regardless of fields supplied by the browser. A mixed batch is saved atomically.
Missing slots do not remove previous assignments; individual slot controls are
available for explicitly removing an official. Duplicate positions, duplicate
people and unregistered referees remain invalid.
