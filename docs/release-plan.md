# Flagtastic Public Launch Plan

## Launch Goal

Flagtastic must be publicly usable by September 27, 2026.

The launch target is not a complete league management platform. The target is a stable public website and operational MVP that lets the league publish and manage the core information people need:

- Teams by branch and category.
- Team rosters.
- Games and scores.
- Standings by branch and category.
- Personal player statistics v1.
- A basic operational workflow for league staff to maintain data.

The project is being built by a two-person team: Bruno and Codex. The plan intentionally favors small, verifiable increments over large rewrites.

## Architecture Direction

The current single-page frontend is useful for early validation, but it is becoming harder to maintain as more workflows are added. The next architecture step is to split the frontend into server-rendered pages backed by the existing FastAPI API.

Target structure:

```text
templates/
  base.html
  teams.html
  games.html
  standings.html

static/
  api.js
  layout.js
  teams.js
  games.js
  standings.js
  style.css

routes/
  web.py
  teams.py
  players.py
  games.py
  standings.py
```

Target web routes:

```text
GET /teams
GET /games
GET /standings
GET / -> redirect to /teams
```

Target API routes remain stable:

```text
GET  /api/teams
POST /api/teams
GET  /api/teams/{team_id}
POST /api/teams/{team_id}/players
GET  /api/teams/{team_id}/players
GET  /api/games
POST /api/games
PATCH /api/games/{game_id}/score
GET  /api/standings
POST /api/games/{game_id}/player-stats
GET  /api/games/{game_id}/player-stats
GET  /api/players/{player_id}/stats
```

## Personal Statistics V1

Personal player statistics are part of the first public release, but the first version must stay intentionally small.

The goal is to support basic public player performance data without delaying the September 27 launch.

### V1 Scope

Statistics are recorded per player, per game.

Minimum fields:

```text
player_game_stats
- id
- game_id
- player_id
- team_id
- touchdowns
- interceptions
- sacks
- flag_pulls
```

The first version should support:

- Manual stat capture by league administrators.
- Listing player stats for a game.
- Showing aggregated player stats publicly.
- Keeping stat totals derived from per-game records, not manually edited as lifetime totals.

### V1 API Direction

```text
POST /api/games/{game_id}/player-stats
GET  /api/games/{game_id}/player-stats
GET  /api/players/{player_id}/stats
```

Expected backend rules:

- The game must exist.
- The player must exist.
- The team must exist.
- The player must belong to the selected team.
- The selected team must be one of the teams in the selected game.
- Stat values must be zero or greater.
- The same player should have only one stat row per game.

### V1 UI Direction

For the first release, avoid a large dedicated statistics dashboard.

Add statistics where they naturally fit:

- On the games page, allow an operational/admin workflow to capture player stats for a game.
- On team rosters, show simple aggregated totals for each player once available.
- On public views, keep statistics readable and compact.

### Out Of Scope For V1

The following are deferred until after launch:

- Advanced offensive/defensive breakdowns.
- Passing yards, rushing yards, receiving yards, completions, attempts, receptions, and tackles.
- League-wide statistical leaderboards.
- Player profile pages with full history.
- CSV imports.
- Automated stat feeds.
- Audit history for each stat correction.

## Access Control Direction

The public launch must account for least-privilege access, even if the first public version ships with a simple implementation.

Access should be modeled by role, not by scattered frontend checks.

### Public Visitor

Public visitors do not need authentication.

Allowed:

- View teams.
- View team rosters.
- View games and scores.
- View standings.

Not allowed:

- Create teams.
- Edit teams.
- Register players.
- Create games.
- Update scores.
- Access administrative screens.

### Player

Players should have the minimum access needed to view their own league context.

Allowed:

- View public league data.
- View their own player profile when authentication exists.
- View their own team membership.

Not allowed:

- Register themselves into arbitrary teams.
- Edit official rosters.
- Edit game scores.
- Manage teams.
- Access league administration.

### Team Representative

Team representatives manage only their assigned team or teams.

Allowed:

- View public league data.
- View assigned team details.
- Submit or maintain roster information for assigned teams.
- Request player changes for assigned teams, depending on the final approval flow.

Not allowed:

- Edit other teams.
- Update official game scores unless explicitly delegated.
- Change standings directly.
- Manage league-wide settings.
- Manage users outside their team scope.

### League Administrator

League administrators manage league operations.

Allowed:

- Create and edit teams.
- Register and manage players.
- Create games.
- Update scores.
- Manage standings indirectly through scores.
- Manage user roles and team assignments.

Not allowed:

- Bypass audit-sensitive workflows once audit logging exists.
- Change production data without traceability in future versions.

### Access Control Implementation Path

Access control should be introduced in stages:

1. Separate public pages from operational/admin pages.
2. Keep all write operations behind backend checks.
3. Add authentication.
4. Add role-based authorization.
5. Add team-scoped permissions for representatives.
6. Add audit logging for administrative actions.

Frontend visibility is not security. Buttons and forms may be hidden in the UI, but the backend must enforce the actual permission rules.

## Sprint 1: Multipage Architecture

Target dates: September 14-16, 2026

Goal: Replace the growing single-page structure with maintainable pages.

Tasks:

- Create `templates/base.html` with shared layout, sidebar, logo, and common assets.
- Create `templates/teams.html`.
- Add `GET /teams`.
- Redirect `GET /` to `/teams`.
- Replace hash navigation with real links.
- Move teams-specific markup out of the current single template.
- Keep `teams.js` focused only on the teams page.
- Create `templates/games.html` and `GET /games`.
- Create `templates/standings.html` and `GET /standings`.
- Remove old hash-view switching logic after all pages are migrated.

Definition of done:

- `/teams`, `/games`, and `/standings` can be loaded directly.
- Browser refresh keeps the user on the same page.
- Each page loads only the JavaScript it needs.
- Existing API tests pass.
- CI is green.

## Sprint 2: Public UI Stabilization

Target dates: September 17-20, 2026

Goal: Make the public website usable and presentable for league users.

Tasks:

- Stabilize the dark visual theme.
- Keep the sidebar retractable without hiding the logo.
- Improve the teams page:
  - Filter by branch and category.
  - Keep team cards readable with many teams.
  - Keep roster display clear.
- Improve the games page:
  - Make games and scores easy to scan.
  - Keep score update workflows operational.
- Improve the standings page:
  - Use a professional table layout.
  - Keep columns clear: team, wins, losses, points for, points against, point difference.
- Validate mobile layout for the public pages.
- Review all visible user-facing copy in Spanish.

Definition of done:

- Public users can understand the site without explanation.
- The three public pages are visually consistent.
- The UI does not feel like a raw internal prototype.
- Existing tests pass.
- CI is green.

## Sprint 3: Personal Statistics V1 And Operational Readiness

Target dates: September 21-24, 2026

Goal: Add the first version of personal player statistics and make the app reliable enough to deploy and operate.

Tasks:

- Add the `player_game_stats` table.
- Add a repository layer for player game statistics.
- Add API contracts for creating and reading player game stats.
- Add `POST /api/games/{game_id}/player-stats`.
- Add `GET /api/games/{game_id}/player-stats`.
- Add `GET /api/players/{player_id}/stats`.
- Validate that a player stat row belongs to a player on one of the teams in the game.
- Prevent duplicate stat rows for the same player in the same game.
- Add tests for personal statistics v1.
- Add a minimal operational UI for capturing stats by game.
- Add a minimal public display for aggregated player stats.
- Confirm all required environment variables are documented.
- Confirm Docker build and runtime behavior.
- Confirm image tagging strategy for future promoted deployments.
- Update README with:
  - Local setup.
  - Test commands.
  - Docker build command.
  - Docker run command.
  - Required environment variables.
- Run a full manual smoke test:
  - Create a team.
  - Register a player.
  - Create a game.
  - Update a score.
  - Capture player stats for a game.
  - View player stats.
  - View standings.
- Review error messages shown to users.

Definition of done:

- Personal statistics v1 works end to end.
- Personal statistics v1 is covered by focused API tests.
- The app can be run locally from documentation.
- Docker image builds cleanly.
- Manual core flow works end to end.
- CI is green.

## Sprint 4: Launch Buffer

Target dates: September 25-27, 2026

Goal: Stabilize the release. Avoid new feature work unless it fixes a launch blocker.

Tasks:

- Freeze non-critical features.
- Fix launch-blocking bugs.
- Validate public pages on desktop.
- Validate public pages on mobile.
- Validate production-like environment variables.
- Create final release tag.
- Confirm final container image.
- Write post-launch backlog.

Definition of done:

- The public site is functional by September 27, 2026.
- Core public pages work.
- Operational workflows work.
- CI is green.
- Known limitations are documented.

## Deferred Until After Public Launch

The following items are important, but should not block the September 27 launch unless business requirements change:

- Full authentication UI.
- Complete role management UI.
- Audit logging.
- Advanced player statistics beyond the v1 scope.
- League-wide statistical leaderboards.
- Full player profile pages.
- Player self-service flows.
- Team logo uploads.
- Season management.
- Playoff brackets.
- Payment workflows.
- Notification system.
- Frontend framework migration.

## Immediate Next Step

Start Sprint 1 by extracting the shared layout into `templates/base.html`, then migrate only the teams page to `/teams`.

Do not migrate games or standings until `/teams` is working and CI is green.
