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
  roster.html
  games.html
  standings.html

static/
  api.js
  layout.js
  teams.js
  roster.js
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
GET /teams/{team_id}/roster
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
POST /api/weeks/{week}/player-stats/import
GET  /api/weeks/{week}/player-stats
GET  /api/players/{player_id}/stats
```

## Personal Statistics V1

Personal player statistics are part of the first public release, but the first version must stay intentionally small.

The goal is to support basic public player performance data without delaying the September 27 launch.

### V1 Scope

Statistics are recorded per player and jornada. Each import is the complete jornada snapshot across all branches, categories, and teams.

Minimum fields:

```text
player_week_stats
- id
- week
- player_id
- team_id
- points
- receptions
- interceptions
- sacks
- tackles
- passes_completed
- passes_attempted
```

The first version should support:

- Complete-jornada Excel imports by league administrators.
- Resolving players by branch, category, team, and jersey number.
- Listing player stats for a jornada.
- Showing aggregated player stats publicly.
- Showing the top five players for each metric by branch and category.
- Keeping stat totals derived from weekly records, not manually edited as lifetime totals.

### V1 API Direction

```text
POST /api/weeks/{week}/player-stats/import
GET  /api/weeks/{week}/player-stats
GET  /api/players/{player_id}/stats
GET  /api/statistics/leaderboards
```

Expected backend rules:

- The jornada must be greater than zero.
- The player must exist.
- The team must exist.
- The player must belong to the selected team.
- The branch, category, team, and jersey number must match one roster membership.
- Stat values must be zero or greater.
- The same player should have only one stat row per team and jornada.

### V1 UI Direction

Add statistics where they naturally fit:

- On the statistics page, allow an operational/admin workflow to import a complete jornada workbook.
- On dedicated team roster pages, show each player's photo, AKA, legal name, jersey, and basic roster data.
- On a public statistics page, show compact top-five leaderboards.

### Out Of Scope For V1

The following are deferred until after launch:

- Advanced offensive/defensive breakdowns.
- Passing yards, rushing yards, receiving yards, completions, attempts, receptions, and tackles.
- Player profile pages with full history.
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

The team creator is assigned atomically even when the account has multiple
roles. Representatives maintain the logo, Head Coach, Coach and Manager, and
use a private dashboard for standings, team totals, and per-player statistics.

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
- Assign one or more referees to games.
- Assign a field from 1 through 8 to every newly scheduled game.

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

### Referee

Referees have an authenticated, private assignment view.

Allowed:

- View public league data.
- View only the games assigned to their own account.

Not allowed by the referee role alone:

- View another referee's private schedule.
- Create games or update official scores.
- Manage teams, users, or role assignments.

Roles are cumulative rather than mutually exclusive. A single account may be
a player, referee, and league administrator; each capability is evaluated
independently so operational access never hides the player dashboard.

Implemented status: stages 1-5 are active. Administrative actions are hidden for public visitors and enforced again by backend dependencies.

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
  - Navigate each team to a dedicated roster page.
- Keep roster display and authorized roster management isolated in `/teams/{team_id}/roster`.
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

- Add the `player_week_stats` table.
- Add a repository layer for weekly player statistics.
- Add API contracts for importing and reading jornada statistics.
- Add `POST /api/weeks/{week}/player-stats/import`.
- Add `GET /api/weeks/{week}/player-stats`.
- Add `GET /api/players/{player_id}/stats`.
- Resolve every stat row against an existing roster using division, team, and jersey.
- Prevent duplicate stat rows for the same player, team, and jornada.
- Add tests for personal statistics v1.
- Add an operational UI for importing a complete jornada.
- Add a minimal public display for aggregated player stats.
- Import `.xlsx` files atomically by jornada.
- Publish top-five leaderboards by branch, category, and statistic.
- Add player self-registration and a personal dashboard.
- Require a validated profile photo, accept an optional AKA, and reuse that identity in dashboards, rosters, and leaderboards.
- Let representatives create and automatically manage their teams.
- Let players join one team per branch and category.
- Show each player's totals and team standings position.
- Rank passing completion percentage with the jornada 4 / 30-attempt rule.
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

### Responsive verification

Desktop Chrome and a Pixel 5 viewport were exercised against the running local
application for Teams, Games, Standings, Statistics, and the dedicated Roster
page. Mobile navigation now starts as a compact branded bar with the logo and
hamburger visible; opening the control reveals the full navigation. Forms and
leaderboards collapse to one column, standings retain horizontal table scrolling,
and roster and game cards remain readable without horizontal page overflow.

## Deferred Until After Public Launch

The following items are important, but should not block the September 27 launch unless business requirements change:

- Complete role management UI.
- Audit logging.
- Advanced player statistics beyond the v1 scope.
- Approval workflow for player team-membership requests.
- Season management.
- Playoff brackets.
- Payment workflows.
- Notification system.
- Frontend framework migration.

## Immediate Next Step

The automated Sprint 3 release smoke test now covers one administrator, one
representative, one player, and an anonymous visitor in
`tests/test_release_smoke.py`. Keep that test in the CI release gate, perform
the corresponding browser walkthrough, and then freeze feature work. Sprint 4
is reserved for responsive verification, launch-blocking fixes, deployment,
and release documentation.

Multi-role authorization and private referee schedules are now part of the
release gate. The administrator assigns referees from the games page, while
`/referee/games` lists only the authenticated referee's assignments. Automated
coverage verifies that an administrator who is also a player and referee keeps
all three capabilities.

Game records now carry fields 1-8 and expose them to teams and assigned
officials. Each role sheet has named slots for Referee, Down Judge, Field Judge,
Side Judge, and Statistician; Referee and Down Judge are the required core.
Administrators can upload an official schedule image, inspect its OCR text,
correct every proposed field and position, and explicitly confirm the result.
Analysis itself never changes official data. Existing players can update AKA
from their dashboard, and that public name is used on official assignments.
