# Flagtastic Architecture

Flagtastic is a platform for managing a flag football league. The current application focuses on registering teams, managing rosters, validating basic eligibility rules, and creating games between teams.

The project follows a deliberately lightweight layered architecture. The current priority is to keep the domain clear, preserve data integrity, and allow the system to grow without introducing premature abstractions.

## Architectural Goals

- Keep the HTTP API simple and predictable.
- Separate input contracts from persistence logic.
- Model players as reusable people across multiple teams.
- Protect critical integrity rules at the database level.
- Keep league rules visible and covered by tests.
- Make it easy to evolve toward seasons, statistics, and leaderboards.

## Overview

```mermaid
flowchart TD
    Client[HTTP Client / Frontend]
    Static[HTML, CSS, JavaScript]
    App[FastAPI app]
    Routes[API Routes]
    Dependencies[Authentication and authorization]
    Models[Pydantic Models]
    Repositories[Repositories]
    DB[(PostgreSQL)]
    Tests[pytest + TestClient]

    Client --> App
    Static --> Client
    App --> Routes
    Routes --> Dependencies
    Routes --> Models
    Routes --> Repositories
    Repositories --> DB
    Tests --> App
    Tests --> DB
```

The application starts in `main.py`, creates the FastAPI instance, mounts static assets, and registers the application routers. Database schema changes are managed separately through versioned Alembic migrations.

## Layers

### Application

Main file: `main.py`

Responsibilities:

- Create the FastAPI instance.
- Register routers.
- Expose the `GET /live` health check.

### Contracts

Main file: `models.py`

Responsibilities:

- Define Pydantic models that validate incoming payloads.
- Keep basic shape and range validation close to the API boundary.

Current models:

- `TeamCreate`: identity, division, and optional Head Coach, Coach, and Manager.
- `TeamStaffUpdate`: editable public staff names for an existing roster.
- `PlayerCreate`: name, CURP, age, and jersey number.
- `GameCreate`: home team and away team.
- `UserCreate`: email, name, password, and role.
- `LoginRequest`: normalized email and secret password input.

### HTTP Routes

Main folder: `routes/`

Responsibilities:

- Define public API endpoints.
- Translate domain or persistence errors into HTTP responses.
- Validate request flow rules that depend on existing resources.
- Delegate data operations to repositories.

Current routers:

- `routes/auth.py`: login, current-session identity, and logout.
- `routes/teams.py`: team registration and listing.
- `routes/players.py`: player registration and roster listing by team.
- `routes/games.py`: game creation and listing.
- `routes/statistics.py`: Excel imports, game statistics, player totals, and leaderboards.

### Dependencies

Main folder: `dependencies/`

Responsibilities:

- Resolve the authenticated user from the `HttpOnly` session cookie.
- Enforce league-administrator permissions for league-wide writes.
- Restrict roster changes to administrators or assigned team representatives.
- Return consistent `401` and `403` responses without relying on frontend visibility.

### Repositories

Main folder: `repositories/`

Responsibilities:

- Open PostgreSQL connections.
- Execute SQL queries.
- Control transactions with `commit` and `rollback`.
- Convert database results into dictionaries.
- Encapsulate queries by entity or aggregate.

Current repositories:

- `repositories/teams.py`
- `repositories/players.py`
- `repositories/games.py`
- `repositories/users.py`
- `repositories/statistics.py`
- `repositories/representative_dashboard.py`

### Services

Main folder: `services/`

Responsibilities:

- Coordinate business rules that span repositories.
- Keep authentication decisions separate from password persistence.
- Return public data without exposing credential hashes.

Current services:

- `services/auth.py`: credential authentication and account-status checks.
- `services/statistics_import.py`: structured workbook parsing and row validation.

### Database

Main file: `database.py`

Responsibilities:

- Resolve `DATABASE_URL`.
- Create psycopg connections using `dict_row`.
- Manage schema evolution through versioned Alembic migrations in `migrations/`.

Current engine:

- PostgreSQL
- Python client: `psycopg`

## Request Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant R as FastAPI route
    participant M as Pydantic model
    participant Repo as Repository
    participant DB as PostgreSQL

    C->>R: HTTP request
    R->>M: Validate payload
    R->>Repo: Execute requested use case
    Repo->>DB: SQL query / transaction
    DB-->>Repo: Row(s)
    Repo-->>R: dict / list
    R-->>C: JSON response
```

Example for registering a player:

1. The client calls `POST /api/teams/{team_id}/players`.
2. FastAPI validates the body with `PlayerCreate`.
3. The route verifies that the team exists.
4. The repository finds or creates the player identity by CURP.
5. The repository validates whether the player is already registered in the same branch and category.
6. The repository creates the membership in `team_players`.
7. The route returns `201 Created` or translates conflicts into `409 Conflict`.

## Data Model

```mermaid
erDiagram
    TEAMS ||--o{ TEAM_PLAYERS : has
    PLAYERS ||--o{ TEAM_PLAYERS : joins
    TEAMS ||--o{ GAMES : home_team
    TEAMS ||--o{ GAMES : away_team
    GAMES ||--o{ PLAYER_GAME_STATS : records
    PLAYERS ||--o{ PLAYER_GAME_STATS : earns
    TEAMS ||--o{ PLAYER_WEEK_STATS : represents

    TEAMS {
        int id PK
        text name
        text branch
        text category
        text status
    }

    PLAYERS {
        int id PK
        text name
        text curp UK
        int age
    }

    TEAM_PLAYERS {
        int id PK
        int team_id FK
        int player_id FK
        int jersey_number
    }

    GAMES {
        int id PK
        int home_team_id FK
        int away_team_id FK
    }

    PLAYER_WEEK_STATS {
        int id PK
        int week
        int player_id FK
        int team_id FK
        int points
        int receptions
        int interceptions
        int sacks
        int tackles
    }
```

### Modeling Decisions

A person's identity is separated from their participation in teams.

- `players` represents the person.
- `teams` represents a team registered in a branch and category.
- `team_players` represents a person's membership in a team.
- `games` represents a matchup between two teams.
- `player_week_stats` stores one official row per jornada, player, and team.

This separation allows the same person to play for multiple teams when league eligibility rules allow it.

## Domain Rules

### Teams

- Every team has `name`, `branch`, `category`, and `status`.
- New teams are created with `status = "pending"`.
- League administrators transition teams among `pending`, `active`, and
  `inactive`; the status is operational state, not free-form display text.
- Team directories group records by branch (`Varonil`, `Femenil`, `Mixto`),
  then category (`U6` through `Libre`), and finally by team name.

### Players

- CURP uniquely identifies a person.
- The public roster does not expose CURP.
- Public roster identity includes the optional AKA and profile-photo URL.
- A player may participate in teams from different branches.
- A player may participate in teams from different categories.
- A player may not participate in two teams within the same branch and category combination.
- A player may not be registered twice in the same team.
- Jersey numbers must be unique within each team.
- The same jersey number may be reused across different teams.

### Games

- A game has a home team and an away team.
- Both teams must exist.
- A team cannot play against itself.
- Official workbook imports pair consecutive 15-row team blocks within the same division.
- Imported scores are inferred from touchdowns and conversions; incomplete tied reconstructions use defensive events as a deterministic one-point tiebreak.

## Data Integrity

The database protects structural constraints:

```text
players.curp UNIQUE
team_players(team_id, player_id) UNIQUE
team_players(team_id, jersey_number) UNIQUE
```

Foreign keys use `ON DELETE CASCADE` to delete related memberships or games when a team or player is deleted.

Rules that need league context, such as preventing a player from registering twice in the same branch and category, are currently validated in the repository layer.

## Current Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/live` | Application health check |
| `POST` | `/api/auth/login` | Authenticates credentials and creates a session cookie |
| `GET` | `/api/auth/me` | Returns the user associated with an active session |
| `POST` | `/api/auth/logout` | Revokes the current session and removes its cookie |
| `POST` | `/api/teams` | Creates a team |
| `GET` | `/api/teams` | Lists teams |
| `PUT` | `/api/teams/{team_id}/logo` | Replaces a team logo; administrators or its assigned representatives only |
| `PATCH` | `/api/teams/{team_id}/staff` | Replaces public Head Coach, Coach, and Manager fields; team managers only |
| `PATCH` | `/api/teams/{team_id}/status` | Changes pending, active, or inactive state; league administrators only |
| `PATCH` | `/api/teams/{team_id}/name` | Corrects only the public team name; league administrators only |
| `PUT` | `/api/teams/{team_id}/representatives/{user_id}` | Links an existing representative account to a historical team; league administrators only |
| `DELETE` | `/api/teams/{team_id}/representatives/{user_id}` | Removes one incorrect team assignment without deleting the account; league administrators only |
| `GET` | `/api/teams/representative-assignments` | Lists current team ownership for verification in the league administration UI |
| `GET` | `/api/me/representative-dashboard` | Returns standings and statistics only for the authenticated representative's teams |
| `DELETE` | `/api/teams/{team_id}` | Deletes a team and dependent records; league administrators only |
| `POST` | `/api/teams/{team_id}/players` | Registers a player in a team |
| `GET` | `/api/teams/{team_id}/players` | Lists a team's roster |
| `POST` | `/api/games` | Creates a game |
| `GET` | `/api/games` | Lists games |
| `PATCH` | `/api/games/{game_id}/score` | Updates a game's score |
| `GET` | `/api/standings` | Lists standings by branch and category |
| `POST` | `/api/weeks/{week}/player-stats/import` | Atomically replaces a complete jornada from `.xlsx` |
| `POST` | `/api/statistics/import` | Atomically imports all official `Wk` sheets, statistics, games, and inferred scores |
| `GET` | `/api/weeks/{week}/player-stats` | Lists a jornada's individual statistics |
| `GET` | `/api/players/{player_id}/stats` | Returns a player's derived totals |
| `GET` | `/api/players/{player_id}/profile` | Returns a public profile with identity, teams, standings and statistics |
| `GET` | `/api/statistics/leaderboards` | Returns five leaders per metric and division |
| `DELETE` | `/api/admin/users/{user_id}` | Deletes another user's login account while preserving player history |

The weekly spreadsheet uses `rama`, `categoria`, `equipo`, and `numero` to resolve a roster membership. Player names shown publicly always come from `players.name`, never from imported text. Only the 50 source-event columns are read; formula-helper columns are deliberately excluded to prevent double counting. Completed passes count as both a completion and an attempt, while `Intentos Pase` supplies incomplete attempts.

The games client keeps one API snapshot and filters it locally by `week` and by
the branch/category exposed in each nested team summary. Development standings
can be exercised with `scripts.balance_mock_games`: it fills only per-division
game-count deficits, produces no tied scores, and is safe to rerun once balanced.

## Current Web Pages

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Redirects to `/teams` |
| `GET` | `/teams` | Filterable team directory |
| `GET` | `/teams/{team_id}/roster` | Dedicated team roster and authorized roster management |
| `GET` | `/games` | Games and scores page |
| `GET` | `/standings` | Standings page |
| `GET` | `/statistics` | Public individual leaderboards |
| `GET` | `/login` | Operational user login |

## Frontend

The frontend foundation lives in:

- `templates/base.html`
- `templates/teams.html`
- `templates/roster.html`
- `templates/games.html`
- `templates/standings.html`
- `templates/statistics.html`
- `templates/login.html`
- `static/style.css`
- `static/layout.js`
- `static/api.js`
- `static/teams.js`
- `static/roster.js`
- `static/games.js`
- `static/standings.js`
- `static/statistics.js`
- `static/login.js`
- `static/register.js`
- `static/dashboard.js`

It is currently a lightweight server-rendered HTML, CSS, and JavaScript layer. Shared layout concerns live in `base.html` and `layout.js`. Page-specific behavior lives in the JavaScript file for that page. The teams page is only a directory: selecting a team navigates to its dedicated roster route, keeping directory filtering and roster management as separate responsibilities. The backend remains API-first, so the frontend can evolve without coupling directly to persistence.

### Responsive layout

The shared shell is mobile-first below `820px`. In that range the sidebar becomes a modal drawer over the page instead of consuming document width. The league logo remains visible in the collapsed header, while the backdrop, Escape key, and navigation links close the expanded drawer. Operational forms and resource grids collapse to one column, controls keep a minimum touch target of `44px`, and dense tables scroll inside their own containers with a sticky first column. This keeps the document itself at viewport width and prevents page-level horizontal scrolling.

Responsive behavior belongs in `static/style.css` and `static/layout.js`; page scripts should not calculate viewport dimensions or duplicate drawer state. Any new table must use an existing scroll wrapper such as `.standings-table`, `.users-table-wrapper`, or `.table-scroll`.

## Testing

The test suite uses `pytest` and `fastapi.testclient.TestClient`.

Current coverage:

- Team registration and listing.
- Player registration and roster listing by team.
- Nonexistent team handling when registering players.
- Duplicate jersey protection within the same team.
- CURP reuse as a single identity with multiple valid memberships.
- Duplicate player restriction within the same branch and category.
- Game creation and listing.
- Protection against a team playing against itself.
- Game creation handling for nonexistent teams.
- Player self-registration and session-backed personal dashboards.
- Self-service team membership with one team per division.
- Excel passing-stat validation and week-dependent qualification rules.

Tests clean the database between cases to preserve isolation.

## Configuration and Deployment

The application reads the connection string from `DATABASE_URL`. The value is required: the application and Alembic fail explicitly when it is not configured. Local values are documented in `.env.example`; CI and deployed environments provide the value through environment configuration or secrets.

Schema changes are applied before application startup:

```text
python -m alembic upgrade head
```

The `Dockerfile` builds an image based on `python:3.14-slim`, installs dependencies from `requirements.txt`, copies the project, and starts Uvicorn on `0.0.0.0:8000`.

Profile media is stored in PostgreSQL rather than the application filesystem.
This keeps photos available when containers or Vercel Functions are replaced.
The image excludes local uploads and development dependency directories from
its build context.

Application command:

```text
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Delivery Architecture

GitHub Actions runs the delivery checks on every push and pull request.

The current pipeline validates:

- Alembic migrations against a clean PostgreSQL service before running tests.
- The Python test suite.
- PostgreSQL integration through a service container.
- Docker image builds.
- Deterministic image tags for future promoted deployments.

Container images should be tagged with immutable references, such as a short commit SHA, and release references, such as Git version tags. Branch tags may be useful for development visibility, but deployments should prefer immutable tags.

Avoid using `latest` as a deployment contract.

## Expected Evolution

The current architecture can grow incrementally:

```mermaid
flowchart LR
    Teams[Teams]
    Rosters[Rosters]
    Eligibility[Eligibility]
    Games[Games]
    Stats[Per-game statistics]
    Seasons[Seasons]
    Auth[Authentication and roles]
    Leaderboards[Leaderboards]

    Teams --> Rosters
    Rosters --> Eligibility
    Eligibility --> Games
    Games --> Stats
    Stats --> Seasons
    Seasons --> Auth
    Auth --> Leaderboards
```

The service layer currently owns authentication decisions. As domain rules grow, it can also centralize eligibility rules, scheduling, statistics capture, standings calculations, and administrative permissions.

## Current Conventions

- Routes handle HTTP responses and client-visible errors.
- Repositories are responsible for SQL and transactions.
- Pydantic models validate incoming payloads.
- The database keeps constraints that should not depend only on application code.
- Public responses avoid exposing CURP in rosters.

## Risks and Considerations

- Production deployments must run `alembic upgrade head` as a controlled release step before starting the new application version.
- Domain rules are partially split between routes and repositories; if they grow, extracting services would help.
- Credential authentication, database-backed sessions, and role-based write authorization are implemented.
- Session cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` by default; local non-HTTPS environments must explicitly disable the secure flag.
- CURP privacy must remain explicit as administrative and public endpoints are added.
- Statistics imports replace one game's snapshot in a single transaction, so invalid workbooks cannot partially alter public totals.

## Player Accounts And Dashboard

`users.player_id` links one login to one global player identity. A player may
claim an existing roster identity only when normalized name, CURP, and age
match; a player identity can be linked to only one login. The personal
dashboard is resolved from the authenticated session and never accepts a
player identifier from the browser.

Representatives may create teams. The creator is inserted into
`team_representatives` in the same transaction, giving that user management
rights only over the new team. Assignment uses the authenticated user id, not
the legacy primary-role string, so cumulative-role users are linked correctly.
Teams created before this behavior do not contain reliable creator history.
An administrator must therefore select the correct representative explicitly;
the application never guesses ownership from roster names or account data.
The assignment write accepts the legacy primary role as well as the cumulative
`user_roles` grant so accounts created before the multi-role migration remain
manageable.
Players join rosters directly in V1 while the
existing one-team-per-division and unique-jersey constraints remain active.

### Representative Dashboard And Team Staff

`teams.head_coach`, `teams.coach`, and `teams.manager` are nullable public
metadata accepted during registration and editable by a team manager. The
representative dashboard begins with `team_representatives`, then combines
official standings, roster membership, and aggregates from
`player_week_stats`. It never accepts a user id from the browser, preventing a
representative from requesting another representative's operational view.
Player rows link to public profiles; CURP and credentials are never selected.

## Passing Leaderboard

Passing rows store completed and attempted passes. Completion percentage is
derived from aggregate totals and is never persisted separately. Through
jornada 3, every player with at least one attempt qualifies. Beginning with
jornada 4, a player needs at least 30 cumulative attempts in the division.
The ranking sorts by percentage, then attempts, then player name.

The official V1 leaderboard catalog is: completion percentage, receptions,
points, tackles, interceptions, and sacks.

Administrators import the per-game source rows from `/statistics`. The page
provides the canonical `.xlsx` template and a game selector; a successful
import replaces that game's complete statistics snapshot atomically.

## Role Administration

The first trusted `league_admin` is created from a local terminal. Subsequent
roles are granted through `/admin/users`; both listing users and changing roles
are protected by the backend administrator dependency. Responses never include
password hashes or CURP, and administrators cannot demote themselves.

Administrators may also delete another account from this page, but cannot delete
their own active account. Account deletion revokes access by cascading sessions,
roles and representative assignments. A linked `players` row is deliberately
preserved, so rosters, game history and individual statistics do not disappear.

Administrators create non-player staff accounts through `POST /api/admin/users`.
The request accepts cumulative operational roles but deliberately rejects the
`player` role, because player identity must be claimed through the CURP-backed
self-registration flow. Staff-only accounts therefore need no CURP, age, photo,
or player record; a league president can hold `league_admin` and `referee`
simultaneously.

Assigned representatives and league administrators can replace a team's logo
from its roster page. `require_team_manager` verifies ownership server-side;
hiding the form for other roles is only a presentation concern.

Public player profiles are available at `/players/{player_id}` and are linked
from roster entries, leaderboards and player rows in administration. Their API
read model reuses the dashboard's season totals, memberships and standings but
never includes CURP, email, account roles or credentials.
These accounts start with `must_change_password = true`. Login creates the
session but redirects to `/change-password`; protected dependencies reject that
session until the current password is verified and replaced.

Authorization is cumulative. `user_roles` stores one or more roles per account:
`league_admin`, `team_representative`, `player`, and `referee`. The legacy
`users.role` column is maintained during the transition, but authorization
checks use the complete role collection. A promoted player therefore retains
their `player_id`, personal dashboard, and roster membership.

`game_referees` links games to official accounts and records `position`,
`assigned_by`, and `assigned_at`. Supported positions are Referee, Down Judge,
Field Judge, Side Judge, and Statistician. Referee and Down Judge are required
when an administrator confirms a complete imported role; the remaining slots
are optional. This supports two referees plus a statistician for U6, three
referees plus a statistician for normal games, and a fourth referee for finals.
One account and one position can appear only once per game. A referee can read
only their own assignments and position through `GET /api/games/mine/referee`;
referee access does not grant score editing or league administration.

`games.field_number` stores a field from 1 through 8. It is nullable only for
historical imports whose source did not contain venue assignments; manually
created games require it at the API boundary. The same value is exposed in the
public schedule and private referee view.

`games.start_time` stores the scheduled local time separately from the jornada
and field. The referee grid importer updates both field and time after review;
when OCR cannot recognize a time it preserves the existing value instead of
erasing it.

The referee-role image import uses Pillow for safe raster decoding and local
Tesseract OCR. `POST /api/games/referee-schedule/analyze` returns proposals and
recognized source text without writing data. After an administrator reviews
the table, `POST /api/games/referee-schedule/confirm` atomically updates the
selected fields and replaces referee links only for those selected games. This
two-step boundary prevents uncertain OCR output from silently becoming an
official assignment.

The current grid format prints four names in this order: Referee, Down Judge,
Field Judge, Statistician. A five-name finals row inserts Side Judge before the
Statistician. Empty slash-delimited positions remain empty, so a missing Field
Judge does not shift the Statistician into the wrong role. Development data for
schedule testing is created idempotently with
`python -m scripts.seed_referee_schedule`; existing accounts and AKA values are
reused before a technical test account is created.

League administrators can assign, replace, or remove officials from the game
detail view. Assigning an occupied position replaces that position atomically,
which supports last-minute role changes without leaving duplicate assignments.
The write endpoints remain protected by the administrator dependency.

## Game Detail Privacy

`player_week_stats.game_id` links an imported statistical row to the exact
game. Imports backfill this link only when a team has exactly one matching game
in the jornada, avoiding an arbitrary match when a schedule is ambiguous.
Official workbooks retain the source's paired 15-row team blocks, so a team
playing a doubleheader can have a separate player row for each game. Reimports
reuse matching game records and update their inferred scores instead of
deleting them, preserving field, time, and officiating assignments.
Repeated matchups in the same jornada consume distinct game records in source
order. The development seed creates missing teams and deterministic mock roster
identities before importing, making repeated runs safe while keeping real
players and existing memberships intact.

The game detail endpoint always exposes teams, jornada, time, field, and score.
Additional sections follow least privilege:

- Players see only their own row for that game.
- Team representatives see rows for participating teams they represent.
- Referees see the officiating crew but no team statistics.
- League administrators see both team statistics and officiating assignments.
- Anonymous visitors see only public game information.

Private keys are omitted from the response rather than returned as empty data,
so the browser cannot reveal a hidden section that was never authorized.

## Player Profile Media

### Claiming a roster identity

A representative may add a player to a roster before that player has login
credentials. The later self-registration searches the global player identity
by normalized CURP and requires the submitted legal name and age to match. A
successful claim links the new user to the existing `players.id`; it does not
create another player or another `team_players` membership. The existing team
and jersey number are therefore preserved, while the submitted AKA and profile
photo enrich the same public roster record and become available in the player
dashboard. A mismatch is rejected instead of silently attaching the account.

### Bulk roster imports

Team managers may import up to 100 players from UTF-8 CSV or XLSX files with
the canonical columns `nombre`, `curp`, `edad`, and `numero`. CSV imports accept
comma or semicolon delimiters so files exported by regional Excel settings work
without manual conversion. Every row is validated through `PlayerCreate`, and
duplicate CURPs or jersey numbers inside the file report the offending row.
Database writes share one transaction; identity, division, or jersey conflicts
roll back the complete upload instead of leaving a partial roster. Imported
players remain ordinary global identities and can later claim their account
through the CURP-backed registration flow described above.

`players.aka` stores an optional public nickname and
`players.profile_photo_path` stores a generated public filename, while
`profile_photo_data` and `profile_photo_type` store the validated image in
PostgreSQL. New player accounts must submit a raster JPG, PNG, or WebP file no
larger than 5 MB. The server validates its binary signature, never trusts the
client filename, and serves accepted files from `/media/profiles`. This database
persistence works across stateless Vercel Functions; object storage can replace
the repository boundary later without changing public URLs. Players can maintain AKA from their authenticated
dashboard, including accounts created before the field existed. The same public identity presentation is reused in
the personal dashboard, dedicated team rosters, and individual-statistics
leaderboards. AKA is preferred for display, the legal roster name remains
visible as supporting identity, and players without media receive an initials
placeholder rather than a broken image. User responses expose `display_name`,
which prefers AKA for navigation, schedules, and official roles while retaining
the legal `name` for administration and identity checks.
