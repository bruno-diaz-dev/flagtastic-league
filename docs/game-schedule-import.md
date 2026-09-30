# Game schedule import

League administrators analyze an image, XLSX or CSV and review the matched
games before confirming. The browser image reader targets the six-field grid
used by the league. Manual entry, XLSX and CSV support fields 1 through 8.

Image recognition preserves recognized times, including breaks and irregular
intervals. Unreadable times remain empty in the review table. Administrators
must fill the time for each selected game before confirmation; recognized times
can also be corrected. Recognition is not a substitute
for reviewing team matches and times before confirmation.

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

## Verification

- `pytest -q`: API, parser, authorization and persistence tests using the test DB.
- `node --test tests/js/*.test.cjs`: browser time-parsing regressions; also in CI.
- Preview smoke test: analyze the actual league image, inspect all proposed
  times and teams, confirm, then repeat and verify that no games are duplicated.
