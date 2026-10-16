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
table. Administrators must fill the time for each selected game before
confirmation; recognized times can also be corrected. Recognition is not a
substitute for reviewing team matches and times before confirmation.

Failed block-OCR time cells receive a second, individual single-line OCR pass.
The review displays registered team names with branch/category in a separate
column. The observed `Pitbulls Ir` glyph error resolves to `Pitbulls Jr` without
collapsing the distinct `Pitbulls Sr` team.

Confirmation is transactional. Repeated identical slots are skipped. Replacing
teams in a slot is allowed only when the existing game has no scores, linked
statistics or assigned officials. Conflicts return HTTP 409 and roll back the
entire batch. Duplicate slots in the same request are rejected. Imports are
serialized to prevent concurrent confirmations from creating the same slot.

Slot identity is week, field and start time. Moving a game to another slot is
not a supported rescheduling operation: it creates a new slot. Administrators
must not use reimport to move games that already exist.

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

Referee spreadsheet imports share the same team identity resolver as game
registration. They compare registered participant IDs (including friendly guests)
within the jornada, then use field/time to distinguish repeated pairings. Joined
names, explicit divisions, Lobos Inf and the U12 mixto convention therefore
resolve consistently in both imports. Ambiguous games and unknown referees
remain warnings; importing never creates referee accounts.
