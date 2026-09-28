# Flagtastic League

Flagtastic League is the production platform for managing the Flagtastic
Football League. It provides public schedules, standings, rosters, player
profiles, and leaderboards together with private workflows for players, team
representatives, referees, and league administrators.

- Production: <https://flagtastic-league.vercel.app>
- API docs: `/docs` and `/redoc`
- Architecture: [`docs/architecture.md`](docs/architecture.md)
- Release plan: [`docs/release-plan.md`](docs/release-plan.md)
- Operations: [`docs/observability.md`](docs/observability.md)

## Product Capabilities

### Public

- Browse teams by branch and category and open dedicated roster pages.
- View player photos, AKA, legal roster names, numbers, ages, and team staff.
- Open public player profiles without exposing CURP, email, roles, or credentials.
- Filter games by jornada, branch, and category and inspect game details.
- Consult division standings with team logos and calculated records.
- View top-five individual leaderboards by branch and category.
- Read the integral privacy notice at `/privacy`.

### Players

- Create an account linked to an existing roster identity through CURP.
- Upload a required profile photo and maintain an optional league AKA.
- Join an eligible team with a jersey number from the personal dashboard.
- See personal teams, standings, season totals, and game-level statistics.

### Team representatives

- Create teams and become their representative automatically.
- Manage only explicitly assigned teams.
- Update team logos and staff: Head Coach, Coach, and Manager.
- Add, edit, deactivate, and photograph roster players.
- Search active player accounts by legal name or AKA and add an eligible
  existing identity without creating a duplicate player.
- Import rosters from CSV or XLSX and download the CSV template.
- View team standings, records, roster totals, and player statistics.

### Referees

- View only their own pending and completed assignments.
- See jornada, field, official position, and game details.
- Combine the referee role with player, representative, or administrator roles.

### League administrators

- Approve or reject teams, rename teams, manage representatives, and delete
  erroneous teams.
- Create staff accounts, grant cumulative roles, and delete login accounts
  while preserving historical sports data.
- Schedule games, record scores, and manage official assignments.
- Import a complete game role from its operational XLSX layout or a CSV, with
  team matching and administrator review before any game is created.
- Upload a role image for OCR-assisted game and official assignment review.
- Import jornada statistics and inspect both teams in game-level statistics.

## Domain Rules

Player identity is separate from roster membership. A player may belong to
multiple teams across different branch/category combinations, but cannot join
two teams in the same division. Jersey numbers are unique only within a team.
CURP uniquely resolves the person and remains private administrative data.

Statistics are stored per jornada and linked to a game, team, and player. The
official workbook resolves players from branch, category, team, and jersey
number; spreadsheet names are not treated as authoritative identities.

Passing percentage is completed passes divided by attempted passes. During the
first three jornadas there is no minimum; after jornada 3, a player needs at
least 30 attempts to qualify for the passing leaderboard.

| Statistic | Leaderboard |
|---|---|
| Passing completion | El Francotirador |
| Receptions | Manos de Acero |
| Points | Maquina de Puntos |
| Tackles | El Muro |
| Interceptions | Cazador Aereo |
| Sacks | Cazador de QBs |

## Architecture

The application is a layered FastAPI monolith with a server-rendered frontend:

```text
Browser (Jinja, CSS, vanilla JavaScript)
                  |
             FastAPI routes
                  |
       services and authorization
                  |
             repositories
                  |
          PostgreSQL (Supabase)
```

- `main.py` assembles the application, pages, media, and health endpoints.
- `routes/` owns HTTP validation and role boundaries.
- `services/` owns authentication, media validation, OCR, and import parsing.
- `repositories/` owns PostgreSQL queries and database read models.
- `models.py` contains Pydantic contracts.
- `migrations/` is the authoritative Alembic schema history.
- `templates/` and `static/` implement the responsive interface.

Profile photos and team logos are stored in PostgreSQL so they remain available
across stateless Vercel deployments. The ignored local `uploads/` directory is
legacy/test output, not the production media store.

Versioned logos and generated profile-photo URLs are cached immutably by the
browser and Vercel CDN. Collection views lazy-load and asynchronously decode
their images so large leagues do not issue one database request per off-screen
team or player during initial rendering.

Authenticated roster reads resolve the session identity in one query and load
team metadata, players, and team-scoped permission through one database
connection. This avoids repeated Supabase connection setup on the highest-use
team detail flow.

See [`docs/architecture.md`](docs/architecture.md) for data ownership,
authorization boundaries, and detailed flows.

## Technology

- Python 3.14, FastAPI, Pydantic, Jinja, and Uvicorn
- PostgreSQL with Psycopg and Alembic
- Vanilla JavaScript and responsive CSS
- OpenPyXL for workbooks; Pillow and Tesseract bindings for images and OCR
- pytest and FastAPI TestClient
- GitHub Actions, Docker/GHCR, Vercel, and Supabase
- Sentry, Vercel Runtime Logs, Supabase Logs Explorer, and Better Stack

## Repository Layout

```text
flagtastic-league/
|-- main.py                 # Application assembly and page routes
|-- database.py             # PostgreSQL connection boundary
|-- models.py               # Pydantic contracts
|-- observability.py        # Structured logs and Sentry
|-- settings.py             # Environment-backed settings
|-- routes/                 # HTTP API endpoints
|-- dependencies/           # Authentication and authorization
|-- services/               # Domain, import, OCR, and media services
|-- repositories/           # PostgreSQL access and read models
|-- migrations/             # Alembic migrations
|-- templates/              # Jinja templates
|-- static/                 # CSS, JavaScript, and assets
|-- scripts/                # Controlled admin/data utilities
|-- tests/                  # Unit, integration, and smoke tests
|-- docs/                   # Architecture, release, and operations docs
|-- .github/workflows/      # CI pipeline
|-- Dockerfile
|-- alembic.ini
`-- requirements.txt
```

## Local Development

### Prerequisites

- Python 3.14
- PostgreSQL 17 or newer
- Tesseract OCR only for local referee-schedule recognition

```powershell
git clone <repository-url>
cd flagtastic-league
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Start PostgreSQL with Docker:

```powershell
docker run -d `
  --name flagtastic-postgres `
  -e POSTGRES_USER=flagtastic `
  -e POSTGRES_PASSWORD=flagtastic `
  -e POSTGRES_DB=flagtastic `
  -p 5432:5432 `
  -v flagtastic-postgres-data:/var/lib/postgresql/data `
  postgres:18
```

Configure local HTTP, migrate, and start the server:

```powershell
$env:DATABASE_URL="postgresql://flagtastic:flagtastic@localhost:5432/flagtastic"
$env:SESSION_COOKIE_SECURE="false"
python -m alembic upgrade head
uvicorn main:app --reload
```

Open <http://127.0.0.1:8000>. `DATABASE_URL` is mandatory; both the application
and Alembic fail explicitly when it is absent.

### Environment variables

| Variable | Required | Purpose |
|---|---:|---|
| `DATABASE_URL` | Yes | PostgreSQL connection for the app and Alembic |
| `TEST_DATABASE_URL` | Tests | Isolated local test database |
| `SESSION_COOKIE_SECURE` | Production | Keep `true`; use `false` only for local HTTP |
| `APP_ENV` | No | Environment name included in telemetry |
| `LOG_LEVEL` | No | Structured application log level |
| `SENTRY_DSN` | Production | Enables Sentry when configured |
| `SENTRY_TRACES_SAMPLE_RATE` | No | Trace sampling rate |
| `SENTRY_RELEASE` | No | Explicit release; Vercel Git SHA is the fallback |

Never commit database URLs, DSNs, cookies, tokens, or production credentials.

## Database Migrations

Alembic migrations are the only supported schema-change mechanism:

```powershell
python -m alembic current
python -m alembic upgrade head
```

Before merging a migration, verify both directions on an isolated database:

```powershell
python -m alembic upgrade head
python -m alembic downgrade base
python -m alembic upgrade head
```

Do not run `stamp head` unless the physical schema already matches the complete
migration history.

## Tests and CI

Create and migrate an isolated local test database:

```powershell
docker exec flagtastic-postgres `
  psql -U flagtastic -d postgres `
  -c "CREATE DATABASE flagtastic_test;"

$env:TEST_DATABASE_URL="postgresql://flagtastic:flagtastic@localhost:5432/flagtastic_test"
$env:DATABASE_URL=$env:TEST_DATABASE_URL
python -m alembic upgrade head
pytest
```

Coverage includes sessions, cumulative roles and least privilege, team and
roster administration, imports and eligibility, dashboards, games, officials,
statistics, leaderboards, pages, observability, and release smoke behavior.

GitHub Actions runs for pull requests and pushes to `main`. It installs and
checks dependencies, compiles Python, performs a full migration
upgrade/downgrade/upgrade cycle, runs pytest, and builds a Docker image.
Non-PR images are published to GHCR. Changes should reach `main` through a pull
request and Vercel Preview deployment before production promotion.

## Administrative Utilities

Create or promote the first trusted administrator:

```powershell
python -m scripts.create_admin `
  --email admin@flagtastic.com `
  --name "League Admin"
```

An existing player or representative keeps the same identity and password and
receives the administrator role.

Seed a controlled local environment from the official workbook:

```powershell
python -m scripts.seed_statistics_workbook "C:\path\to\Stats ALL.xlsx"
```

The command is idempotent: it creates missing teams and mock roster identities,
reuses matching games, and imports game-scoped statistics. It is intended for
development or migration work, not normal production traffic.

For deterministic standings UI data:

```powershell
python -m scripts.balance_mock_games
```

## Deployment and Operations

Production runs on Vercel with PostgreSQL supplied by Supabase. The production
database must be upgraded to the repository's Alembic head before code that
depends on a new schema is promoted. Secure session cookies remain enabled.

- `GET /live` verifies the FastAPI process.
- `GET /ready` verifies PostgreSQL and returns `503` without database details
  when the application is not ready.

Sentry captures scrubbed errors, logs, and sampled traces. Vercel Runtime Logs
cover deployments and requests, Supabase Logs Explorer covers PostgreSQL, and
Better Stack checks `/live` and `/ready` every three minutes with email alerts.
See [`docs/observability.md`](docs/observability.md) for configuration, privacy
safeguards, and incident response.

## Security and Privacy

- Authentication uses random database sessions. Only a SHA-256 token hash is
  stored; the raw token uses an `HttpOnly`, `SameSite=Lax`, production `Secure`
  cookie.
- Roles are cumulative; `user_roles` is the authorization source of truth.
- Representatives are scoped to explicitly linked teams.
- Operational staff must replace their initial password before protected work.
- CURP is private and used only for identity matching and administration.
- Public responses exclude hashes, tokens, CURP, email, and authorization data.
- Supabase Row Level Security is defense in depth; FastAPI still enforces every
  authorization boundary.
- Telemetry scrubs credentials, cookies, CURP, files, and request bodies.

## Current Status

The platform is deployed and in active use while receiving release-hardening
and mobile usability improvements. Teams, rosters, profiles, games, standings,
statistics imports, leaderboards, role dashboards, referee assignments,
authentication, administration, privacy, and monitoring are implemented. Open
work belongs in tracked issues or the release plan instead of being described
as completed functionality here.

## License

This project is developed for the Flagtastic Football League. No public license
has been granted.
