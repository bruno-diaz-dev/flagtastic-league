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
