# Live game capture

The public match detail page contains a live scoreboard, reverse-entry-order play feed, and player sheet. Only accounts explicitly carrying the referee role may start capture, add events, and finish a match. League administrators without that role cannot record live events. Referees can capture any scheduled game, matching the existing first-score policy; assignment is not an additional requirement.

## Digital sheet

- Complete pass: attempt and completion to passer; reception to receiver.
- Passing touchdown: the same pass metrics, six team points, six receiver points, and six passer points in the separate live passing-points column. Passing points are not duplicated in scorer totals.
- Running/return touchdown and successful one/two-point extras: points to the selected scorer and team.
- Safety: two points to the selected team and player.
- Sack, flag removed, interception: select the defending team/player. Flags map to the existing `tackles` statistic.
- Attendance: records presence once per player in the digital sheet; retained in events and live totals.
- Observation: public text, never private referee evaluations or signatures.

The supplied paper has separate referee evaluations/signatures; this release implements sporting capture, not electronic signatures or private evaluations. Public observations must contain only game commentary.

## Time and refresh

The official copies period and clock minutes/seconds from the field clock. This is not an automatically running timer, and the interface imposes no unconfirmed period-length rules. Feed ordering follows entry order, so clock corrections and overtime remain possible. Public clients refresh every 12 seconds during live play, pause when hidden, back off on failures, and stop at completion. The CDN may cache the public feed for five seconds. No WebSocket server or Supabase client key is needed.

## Reliability and finalization

Each client event has a UUID. Identical retries return the existing event without changing score/statistics; reuse with different content is rejected. Failed requests retain the entered form and UUID for explicit retry. There is no offline auto-upload queue. A database game-row lock serializes capture, corrections and finalization. Finalization requires the reviewed session version and rejects ties. It atomically publishes this game's totals to `player_week_stats` and its official score to `games`. It does not add another copy to season totals.

Referees may void live entries with a reason. After completion only administrators may void entries; final totals and score are rebuilt atomically. Voided plays remain visible and staff attribution/reasons remain private in storage. Administrative corrections that would produce a tie are rejected. New entries and reopening a completed session are not supported. Existing administrator score correction remains available; in that case the official final score overrides the event-derived scoreboard.

Legacy final-score/status actions cannot close or postpone active capture. Weekly bulk status changes skip live games. Weekly Excel imports are rejected for jornadas with any live-captured match, preventing silent replacement of audited game statistics. Regular roster and statistics imports continue elsewhere.

## Database

Migration `a2c6f8109d43` follows `9a12e8d4c6f0`. Two additive tables use foreign keys and idempotent schema creation. Both have RLS enabled and no browser write policies; access goes through FastAPI authentication and existing server credentials. Never change an Alembic version marker merely because managed deployment markers differ.
