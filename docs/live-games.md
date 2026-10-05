# Live game capture

The public match detail page contains a live scoreboard, reverse-entry-order play feed, and player sheet. Only accounts explicitly carrying the referee role may start capture, add events, and finish a match. League administrators without that role cannot record live events. Referees can capture any scheduled game, matching the existing first-score policy; assignment is not an additional requirement.

## Digital sheet

- Complete pass: attempt and completion to passer; reception to receiver.
- Passing touchdown: the same pass metrics, six team points, six receiver points, and six passer points in the separate live passing-points column. Passing points are not duplicated in scorer totals.
- Running/return touchdown and successful one/two-point extras: points to the selected scorer and team.
- Safety: two points to the selected team and player.
- Sack, flag removed, interception: select the defending team/player. Flags map to the existing `tackles` statistic.
- Attendance: records presence once per player in the digital sheet; retained in events and live totals.
- The public feed narrates every entry automatically from its event type, team, player and receiver. No description or commentary is required or accepted on new entries. Historical observations remain stored but their free text is not rendered.

The supplied paper has separate referee evaluations/signatures; this release implements sporting capture, not electronic signatures or private evaluations. No free-text public commentary is captured.

## Time and refresh

The official copies period and clock minutes/seconds from the field clock. This is not an automatically running timer, and the interface imposes no unconfirmed period-length rules. Feed ordering follows entry order, so clock corrections and overtime remain possible. Public clients refresh every 12 seconds during live play, pause when hidden, back off on failures, and stop at completion. The CDN may cache the public feed for five seconds. No WebSocket server or Supabase client key is needed.

## Reliability and finalization

Each client event has a UUID. Identical retries return the existing event without changing score/statistics; reuse with different content is rejected. Failed requests retain the entered form and UUID for explicit retry. There is no offline auto-upload queue. A database game-row lock serializes capture, corrections and finalization. Finalization requires the reviewed session version and rejects ties. It atomically publishes this game's totals to `player_week_stats` and its official score to `games`. It does not add another copy to season totals.

Referees may void live entries with a reason. After completion only administrators may void entries; final totals and score are rebuilt atomically. Voided plays remain visible and staff attribution/reasons remain private in storage. Administrative corrections that would produce a tie are rejected. New entries and reopening a completed session are not supported. Existing administrator score correction remains available; in that case the official final score overrides the event-derived scoreboard.

Legacy final-score/status actions cannot close or postpone active capture. Weekly bulk status changes skip live games. Weekly Excel imports are rejected for jornadas with any live-captured match, preventing silent replacement of audited game statistics. Regular roster and statistics imports continue elsewhere.

## Database

Migration `a2c6f8109d43` follows `9a12e8d4c6f0`; `b3d7e9210a54` grants the existing restricted `flagtastic_app` backend role table/sequence access and role-scoped RLS policies. Both tables have RLS enabled and no browser policies; access goes through FastAPI authentication and existing server credentials. Test with the restricted backend role as well as the database owner. Never change an Alembic version marker merely because managed deployment markers differ.


## Preview test rosters

The optional script `scripts/seed_preview_live_players.sql` fills every preview team to at least seven active players. Select project `mqnrrlymoddxgnyadsvy`, begin a transaction, set the explicit preview marker shown in the script, run it and commit. It is not an Alembic migration and must never be applied to production. It preserves existing players and jersey numbers, uses visibly fictional names and provisional TEST identities with synthetic birth dates appropriate to the category, and adds nothing on an unchanged repeat run.


## Touch capture and durable outbox

The referee form opens for a live game. Team and event-type buttons replace repeated dropdown navigation. Dorsal buttons capture immediately when the clearly labeled one-tap toggle is enabled. Complete passes and passing touchdowns preserve the passer per team; tapping the receiver captures the combined event. Incomplete passes and individual statistics capture on the actor button. Disable one-tap to review and submit manually. The field clock is copied by the official and retained, never estimated.

Each capture is committed to IndexedDB before upload, scoped to the game and authenticated referee ID. Pending plays remain separate from the public confirmed timeline and survive reload on the same browser/origin. Ordered background uploads leave capture controls available for the next play. Network timeouts and ambiguous responses reuse the play UUID; the server's existing idempotency check prevents duplicates. A 4xx rejection stops the queue and preserves every later play. Invalid selections (422) can be corrected in place before retry; other rejected plays require review. No request is sent by public/player roles or after the game closes.

Finalization and voiding are blocked while there are local pending writes. No provisional local event changes the public score or published statistics. The current browser must reconnect to upload pending plays; clearing browser data or switching domains/devices does not transfer the outbox. If local storage cannot open, new capture is disabled instead of claiming a play was saved.

Validation includes VM tests for per-team passer retention, non-blocking capture, close guards, durable write failures and ordered/idempotent retries. The isolated mobile browser check uses the actual IndexedDB API, reloads with two unsent plays, reconnects and verifies exactly two published events, correct score, no horizontal overflow and no referee controls for a player. Its API responses are mocked; backend authorization and idempotency remain covered by the existing API tests.
