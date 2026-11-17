# Statistics Upload Size

Vercel limits Function request bodies to 4.5 MB, independently of the
application's 15 MiB workbook validation limit. Increasing the Python limit
does not allow larger requests through the hosting platform.

The browser accepts original XLSX files up to **32 MiB**. Files above
**1000 KiB** are prepared in a browser worker before upload. The prepared file
must fit within **1000 KiB**, below the multipart parser's 1 MiB spooling
threshold as well as Vercel's request limit. The server-side 15 MiB validation
is a separate limit on the received file; large originals are not sent as-is.
SheetJS CE 0.20.3 reads only `Wk` sheets. The worker exports the source columns
A:BA (team, division, event label and 50 event cells), preserving cached values,
sheet names and blank row positions required by the 15-row block parser.
Summary sheets, helper formulas and formatting are excluded from the temporary
upload. The user's original workbook remains unchanged. The server still
performs authorization, parsing, identity validation and transactional writes.

The server ignores repeated `Equipo / Categoria / Estadistica` print headers
and unused week templates. The worker also recognizes empty team cells
whose formulas cache numeric zero, without dropping jersey zero in event cells.
Populated weeks with invalid data still fail instead
of being silently skipped. Both game and player parsers use the same block
reader so a repeated header cannot shift one parser's game identities.

Named game pairs without any recognized player events or attendance on either
side are schedule placeholders, not results. The game parser omits those pairs
before matching teams or inferring scores. It retains each remaining game's
original block index so player statistics after an empty pair keep the correct
match association. Attendance-only records (including jersey zero) and pairs
with data on just one side are retained.

Sources above 32 MiB, preparation failures, and prepared uploads above 1000 KiB
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

## Inconsistent passing counts

Official-sheet imports continue when a QB has more completions than recorded
attempts. The response includes a `warnings` entry identifying the week, sheet,
team, jersey and original counts. The page displays it even if no jerseys were
skipped. Other valid metrics, including the receiver's receptions, still import.
The QB's passing pair is omitted together: existing passing totals for that
player/game are preserved on update; a new record has no credited passing stats.
No attempts are inferred and a valid jersey zero is treated like any other number.
Strict parser callers without a warning collector still reject the inconsistency.

## Confirmed source identities

The league administrator confirmed `Valkirias Blanco` as the workbook label for
`Vikingos Blanco` in **femenil U14**. This fallback is limited to that division
and requires one unambiguous registered target. Literal registered identities
still take precedence; missing or duplicate targets remain errors.

For jornada 3, the administrator also confirmed three mislabeled source pairs:
`Diablos Rojo–Lanceros` and `Diablos Amarillo–UCA` are **femenil U18**, and
`Diablos–Ravens` is **femenil libre**. Both the game reader and the player reader
apply the same correction to those exact paired labels and source divisions.
Other jornadas, ages, names and matchups retain their original divisions.
