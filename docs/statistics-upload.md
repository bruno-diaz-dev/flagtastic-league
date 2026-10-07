# Statistics Upload Size

Vercel limits Function request bodies to 4.5 MB, independently of the
application's 15 MiB workbook validation limit. Increasing the Python limit
does not allow larger requests through the hosting platform.

Official files above 4 MiB are prepared in a browser worker before upload.
SheetJS CE 0.20.3 reads only `Wk` sheets. The worker exports the source columns
A:BA (team, division, event label and 50 event cells), preserving cached values,
sheet names and blank row positions required by the 15-row block parser.
Summary sheets, helper formulas and formatting are excluded from the temporary
upload. The user's original workbook remains unchanged. The server still
performs authorization, parsing, identity validation and transactional writes.

The server ignores repeated `Equipo / Categoria / Estadistica` print headers
and unused week templates. Populated weeks with invalid data still fail instead
of being silently skipped. Both game and player parsers use the same block
reader so a repeated header cannot shift one parser's game identities.

Sources above 15 MiB, preparation failures, and prepared uploads above 4 MiB
are rejected before submission. A platform 413 response produces a size error
even if the response is plain text, rather than a misleading connection error.
The submit button remains disabled while preparation and import are running.

Run `node --test tests/js/statistics_upload.test.cjs` for transport regressions.
Browser verification should include a large official file and compare all
imported source cells and parser results against the original. Never use
production imports as a smoke test: successful imports replace existing data.

## Unknown Jersey Numbers

Both import endpoints skip player records whose jersey number does not exist
in the resolved team's roster. They never create players or assign those stats
to another team's player. Responses include `skipped`, `skipped_count` and
`preserved_weeks`; each skipped record identifies its week, team, division,
jersey number and game index. The page lists the omitted numbers after import,
deduplicating the displayed week/team/number while counting all skipped records.

Weeks with valid records retain complete-week replacement semantics. If every
record in a week has an unknown number, its existing statistics and games remain
unchanged. Unknown teams, duplicate valid players, malformed values and live-game
conflicts still reject the transaction. Game scores are still taken from the
workbook, including when an individual scorer's number is omitted.
