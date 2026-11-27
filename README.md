# Flagtastic League

Flagtastic League is the production platform for managing the Flagtastic
Football League. It provides public schedules, live games, standings, rosters,
player profiles, and leaderboards together with private workflows for players,
team representatives, referees, and league administrators.

- Production: <https://flagtastic.online>
- API docs: `/docs` and `/redoc`
- Architecture: [`docs/architecture.md`](docs/architecture.md)
- Statistics import: [`docs/statistics-upload.md`](docs/statistics-upload.md)
- Game schedule import: [`docs/game-schedule-import.md`](docs/game-schedule-import.md)
- Playoff advancement: [`docs/playoff-advancement.md`](docs/playoff-advancement.md)
- Live games: [`docs/live-games.md`](docs/live-games.md)
- Mobile release: [`docs/mobile-release.md`](docs/mobile-release.md)
- Release plan: [`docs/release-plan.md`](docs/release-plan.md)
- Operations: [`docs/observability.md`](docs/observability.md)

## Product Capabilities

### Public

- Browse teams by branch and category and open roster pages from any
  displayed team name across schedules, standings, statistics, and dashboards.
- View player photos, AKA, legal roster names, numbers, ages, and team staff.
- Open public player profiles without exposing CURP, email, roles, or credentials.
- Filter games by team, jornada, branch, category, or field, grouped by
  jornada and time, with a featured result per jornada.
- Follow a game live: scoreboard, play-by-play feed, and illustrative field
  view, refreshed while the game is in progress.
- See pending playoff games ("Final … en espera de equipos") before their
  teams are decided.
- Consult division standings and top-five leaderboards per division.
- Read the integral privacy notice at `/privacy`.

### Players

- Create an account linked to an existing roster identity through CURP (or a
  provisional identifier with a birth date).
- Upload a required profile photo (large camera images are reduced in the
  browser) and maintain an optional league AKA.
- Join an eligible team with a jersey number from the personal dashboard.
- See personal teams, standings, season totals, and game-level statistics.

### Team representatives

- Create teams and become their representative automatically; manage only
  explicitly assigned teams.
- Roster changes close for representatives on October 16, 2026 at 00:00 in
  `America/Mexico_City`; administrators retain editing access.
- Update team logos and staff (Head Coach, Coach, Manager).
- Add, edit, deactivate, and photograph roster players; reuse existing player
  identities instead of creating duplicates; import rosters from CSV or XLSX.
- View team standings, records, and player statistics on web and mobile.

### Referees

- Appear in a private referee directory visible to signed-in users, with an
  aggregate experience profile and a self-managed AKA and photo (player-referees
  reuse their player photo).
- View only their own pending and completed assignments, with jornada, field,
  position, and the full crew.
- Record final scores and run live capture: plays, attendance check-in,
  corrections, and finalization that publishes score and statistics.
- Combine the referee role with player, representative, or administrator roles.

### League administrators

- Approve, rename, and delete teams; manage representatives; review possible
  duplicate team names.
- Create staff accounts, grant cumulative roles, reset or recover accounts, and
  delete logins while preserving sports history.
- Import the game calendar from XLSX, CSV, or an image (browser OCR) with
  review before any game is created, including pending final and third-place
  slots; move games on the schedule board; schedule friendly games with guest
  teams; postpone, restore, or delete games or a jornada.
- Import referee roles from XLSX, CSV, or images and assign officials manually.
  Role imports identify each game by jornada, field and time and only assign
  officials; a game is moved only when its row is explicitly marked to move.
- Import the official statistics workbook. Imports link statistics to existing
  games only, show progress, and list skipped records with a CSV download.
- Review finals eligibility at `/admin/finals-eligibility`.

Image recognition is an administrative aid, not an authoritative source; every
proposal must be reviewed before confirmation. See
[`docs/game-schedule-import.md`](docs/game-schedule-import.md).

## Domain Rules

Player identity is separate from roster membership. A player may belong to
teams in different divisions but not to two active teams in the same division.
Jersey numbers are unique within a team. CURP (or a provisional identifier)
resolves the person and remains private. Age is the player's completed years,
derived from the CURP birth date or the provisional birth date.

Team identity is name + branch + category, compared case-insensitively. U8,
U10 and U12 are one **Infantiles** division per category: new teams are stored
as `mixto`, historical teams keep their branch, teams may play across branches,
and standings and leaderboards combine every branch.

The game schedule is the source of truth for games. Statistics imports resolve
players from branch, category, team, and jersey number, and only link
statistics to games that already exist; they never create games or write
scores. Unresolved teams, games, or jersey numbers are skipped and reported.
Ambiguous team abbreviations are left for review instead of guessed.

Leaderboards show the top five per division. In unified U8–U12, a player on
several rosters appears once with her best team record; records are never
summed.

| Statistic | Leaderboard |
|---|---|
| Quarterback index | El Francotirador |
| Receptions | Manos de Acero |
| Points | Maquina de Puntos |
| Tackles | El Muro |
| Interceptions | Cazador Aereo |
| Sacks | Cazador de QBs |

The quarterback index (0–100) averages precision (completions ÷ attempts),
productivity (passing points per completion ÷ 2.5, capped at 1), and safety
(1 − interception rate ÷ 10%, floored at 0). A player needs at least 50
cumulative attempts at all times to qualify.

Final and third-place games are created in advance with pending labels and
filled automatically when both semifinals have final scores; a corrected
semifinal updates them until that game starts. Players qualify
for the finals by attending at least half + 1 of their team's regular-season
games (6 games → 4). See [`docs/architecture.md`](docs/architecture.md#finals-eligibility).

## Architecture

The application is a layered FastAPI monolith with a server-rendered frontend
and an Expo client for players, referees, and team representatives:

```text
Browser (Jinja, CSS, vanilla JavaScript)     Expo mobile app (Bearer session)
                  \                                  /
                   +---------- FastAPI routes ------+
                                  |
                      dependencies (authorization)
                                  |
                      services and repositories
                                  |
                         PostgreSQL (Supabase)
```

Profile photos and team logos are stored in PostgreSQL so they survive
stateless Vercel deployments; versioned URLs are cached immutably. See
[`docs/architecture.md`](docs/architecture.md) for layers, data model,
endpoints, and authorization boundaries.

## Technology

- Python 3.14, FastAPI, Pydantic, Jinja, and Uvicorn
- PostgreSQL with Psycopg; Alembic for schema history
- Vanilla JavaScript and responsive CSS; SheetJS (vendored) and Tesseract.js in
  the browser
- Expo SDK 57, React Native, Expo Router, and TypeScript
- OpenPyXL for workbooks; Pillow and pytesseract for images and server OCR
- pytest, Node's test runner, and Playwright
- GitHub Actions, Docker/GHCR, Vercel, and Supabase
- Sentry, Vercel Runtime Logs, Supabase Logs Explorer, and Better Stack

## Repository Layout

```text
flagtastic-league/
|-- main.py                 # Application assembly, pages, media, health
|-- database.py             # PostgreSQL connection boundary
|-- models.py               # Pydantic contracts
|-- observability.py        # Structured logs and Sentry
|-- settings.py             # Environment-backed settings
|-- routes/                 # HTTP API endpoints
|-- dependencies/           # Authentication and authorization
|-- services/               # Domain rules, imports, OCR, media, email
|-- repositories/           # PostgreSQL access and read models
|-- migrations/             # Alembic migrations
|-- templates/              # Jinja templates
|-- static/                 # CSS, JavaScript, vendored libraries, assets
|-- mobile/                 # Expo app for players, referees, representatives
|-- scripts/                # Development data utilities
|-- tests/                  # pytest, tests/js (Node), tests/browser (Playwright)
|-- docs/                   # Architecture, imports, operations; docs/sql twins
|-- .github/workflows/      # CI and CodeQL
|-- Dockerfile
|-- alembic.ini
|-- requirements.txt        # Runtime dependencies
`-- requirements-dev.txt    # Runtime + Alembic + pytest
```

### Mobile application

The mobile client provides player views (`Inicio`, `Posiciones`, `Lideres`,
`Mis Stats`), referee views (`Inicio`, `Mi agenda`, `Historial`), and
representative views (`Inicio`, `Mis equipos`, `Partidos`, `Posiciones`).
`Mi perfil` switches between the account's roles and signs out. Roster editing,
game details, and profile administration open the web application. It uses the
same API and data as the web client.

See [`mobile/README.md`](mobile/README.md) for setup, environment variables,
and builds, and [`docs/mobile-release.md`](docs/mobile-release.md) for
distribution.

## Local Development

### Prerequisites

- Python 3.14
- PostgreSQL 17 or newer
- Node.js 22 for JavaScript, browser, and mobile tests
- Tesseract OCR only for server-side image OCR (referee-role images and the
  server image path of the game calendar). It is installed in the Docker image
  but not available on Vercel, where game-calendar images are read in the
  browser (`static/ocr_loader.js`). XLSX and CSV imports need no OCR.

```powershell
git clone <repository-url>
cd flagtastic-league
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

`requirements.txt` is the runtime set used by Vercel and Docker; Alembic and
pytest are only in `requirements-dev.txt`.

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
and Alembic fail explicitly when it is absent. `.env.example` lists local
values.

### Environment variables

| Variable | Required | Purpose |
|---|---:|---|
| `DATABASE_URL` | Yes | PostgreSQL connection for the app and Alembic |
| `TEST_DATABASE_URL` | Tests | Local test database; `tests/conftest.py` uses it (default `.../flagtastic_test`) instead of `DATABASE_URL` |
| `CI` | CI | When set, tests use `DATABASE_URL` as-is instead of `TEST_DATABASE_URL` |
| `SESSION_COOKIE_SECURE` | Production | Keep `true` (default); use `false` only for local HTTP |
| `PUBLIC_BASE_URL` | Password reset | Origin used in reset links (default `http://127.0.0.1:8000`) |
| `RESEND_API_KEY` | Password reset | Resend API key for reset emails |
| `PASSWORD_RESET_FROM_EMAIL` | Password reset | Sender on a verified Resend domain |
| `APP_ENV` | No | Environment label for logs and Sentry; falls back to `VERCEL_ENV`, then `development` |
| `LOG_LEVEL` | No | Structured log level (default `INFO`) |
| `SENTRY_DSN` | Production | Enables Sentry when set |
| `SENTRY_TRACES_SAMPLE_RATE` | No | Trace sampling rate (default `0.1`) |
| `SENTRY_RELEASE` | No | Explicit release; falls back to `VERCEL_GIT_COMMIT_SHA` |

`VERCEL_ENV` and `VERCEL_GIT_COMMIT_SHA` are supplied by Vercel. Mobile
variables such as `EXPO_PUBLIC_API_URL` are documented in
[`mobile/README.md`](mobile/README.md). Never commit database URLs, DSNs,
cookies, tokens, or production credentials.

## Database Migrations

The current Alembic head is `c5e2a7f19d30`. Vercel deploys `main` on merge and
**never runs migrations**, so a schema change must be applied to Preview and
then Production **before** merging code that reads it. Two paths are
supported:

1. **Alembic**, with the database owner credentials:

   ```powershell
   python -m alembic current
   python -m alembic upgrade head
   ```

2. **SQL twin**, for additive changes: run the idempotent script in
   [`docs/sql/`](docs/sql/) in the Supabase SQL editor (for example
   `docs/sql/add-quarterback-passing-stats.sql`). These scripts do not edit
   `alembic_version`; a later `alembic upgrade head` stays compatible because
   the migration is idempotent.

Rules:

- Always apply to Preview first, verify, then Production.
- A migration that may be applied through the SQL editor must be idempotent and
  ship with a `docs/sql/` twin.
- Never downgrade Preview or Production: several downgrades delete data. Fix
  forward with a new migration.
- Verify the downgrade/upgrade cycle only on a disposable database (CI does
  this on every run).
- Do not run `stamp head` unless the physical schema already matches the
  complete migration history.

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

JavaScript, browser, and mobile tests:

```powershell
node --test tests/js/*.test.cjs

npm install --no-save --no-package-lock playwright@1.62.1
npx playwright install chromium
node tests/browser/live_capture.cjs   # each script in tests/browser runs the same way

cd mobile
npm ci
node --test tests/*.test.mjs
npm run typecheck
```

Browser tests mock the API and need no database.

GitHub Actions runs on pull requests to `main` and pushes to `main`:

| Job | What it does |
|---|---|
| Test | Installs `requirements-dev.txt`, compiles Python, runs Alembic upgrade/downgrade/upgrade on PostgreSQL 18, `pytest`, and `node --test tests/js/*.test.cjs` |
| Docker | Builds the image; pushes to GHCR only for non-PR events |
| Mobile | `npm ci`, mobile tests, type-check, and `expo-doctor` |
| Live capture browser | Playwright scripts in `tests/browser/` on mobile Chromium |
| CodeQL (Analyze Python) | Static analysis; also runs weekly |

## Administrative Utilities

The scripts connect to whatever `DATABASE_URL` points at and have **no
Production guard**. Run them only against local or Preview databases.

Create or promote the first trusted administrator:

```powershell
python -m scripts.create_admin `
  --email admin@flagtastic.com `
  --name "League Admin"
```

An existing player or representative keeps the same identity and password and
receives the administrator role.

Seed a development database from the official workbook:

```powershell
$env:FLAGTASTIC_DATA_TARGET="local"   # or "preview"; never Production
python -m scripts.seed_statistics_workbook "C:\path\to\Stats ALL.xlsx"
```

It creates missing teams and mock roster identities and imports statistics.
Unlike the administrator import, this seed **creates missing games and writes
scores inferred from the workbook**.

Other utilities: `python -m scripts.balance_mock_games` (adds non-tied mock
games so every team in a division has the same count),
`python -m scripts.seed_referee_schedule` (development referee accounts), and
`scripts/seed_preview_live_players.sql` (Preview-only test rosters; see
[`docs/live-games.md`](docs/live-games.md)).

The three Python seed scripts refuse to run unless `FLAGTASTIC_DATA_TARGET`
is `local`, `preview` or `test`: `DATABASE_URL` alone cannot tell Preview
from Production, so the operator confirms the target first.
`scripts.create_admin` is not restricted.

## Deployment and Operations

Production runs on Vercel with PostgreSQL supplied by Supabase. Merging to
`main` deploys Production. Every branch and pull request gets a Vercel Preview
deployment (`vercel.json` enables Git deployments for all branches) backed by
the separate `flagtastic-league-preview` Supabase project through a
Preview-only `DATABASE_URL`. Preview data is test data and may be replaced
freely; production data must never be copied into it. Apply schema changes as
described in [Database Migrations](#database-migrations) before merging.

Upload limits: Vercel rejects request bodies over 4.5 MB before the
application runs. Server-side limits are 15 MiB for statistics workbooks and
game calendars, 10 MiB for referee roles, and 4 MiB (`UPLOAD_MAX_BYTES` in
`settings.py`, below the Vercel cap) for roster imports, profile photos,
referee photos, and team logos; the roster page checks those sizes before
uploading. Only statistics workbooks (above 4 MiB) and registration profile
photos (above 3 MB) are reduced in the browser; every other upload must be
under 4.5 MB in Production.

Password recovery uses Resend and requires `PUBLIC_BASE_URL`, `RESEND_API_KEY`,
and `PASSWORD_RESET_FROM_EMAIL`. Reset links expire after 30 minutes, work once,
and revoke every existing session. The login page does not link to it until the
league has a verified sending domain.

- `GET /live` verifies the FastAPI process.
- `GET /ready` verifies PostgreSQL and returns `503` without database details
  when the application is not ready.

Sentry captures scrubbed errors, logs, and sampled traces. Vercel Runtime Logs
cover deployments and requests, Supabase Logs Explorer covers PostgreSQL, and
Better Stack checks `/live` and `/ready` every three minutes with email alerts.
See [`docs/observability.md`](docs/observability.md).

## Security and Privacy

- Authentication uses random database sessions. Only a SHA-256 token hash is
  stored; the raw token uses an `HttpOnly`, `SameSite=Lax`, production `Secure`
  cookie, or a Bearer header in the mobile app.
- Password reset tokens are also stored only as SHA-256 hashes, expire after
  30 minutes, and never disclose whether a submitted email exists.
- Roles are cumulative; `user_roles` is the authorization source of truth.
- Representatives are scoped to explicitly linked teams.
- Operational staff must replace their initial password before protected work.
- CURP is private and used only for identity matching and administration.
- Public responses exclude hashes, tokens, CURP, email, and authorization data.
- Supabase Row Level Security is defense in depth; FastAPI still enforces every
  authorization boundary.
- Telemetry scrubs credentials, cookies, CURP, files, and request bodies.

## Current Status

The platform is deployed and in active use for the 2026 season. Teams,
rosters, profiles, schedules and schedule imports, live capture, standings,
statistics imports, leaderboards with the quarterback index, playoff
advancement, finals eligibility, role dashboards, referee assignments, the
mobile app, authentication, administration, privacy, and monitoring are
implemented. Open work belongs in tracked issues or the release plan instead
of being described as completed functionality here.

## License

Copyright © 2026 Bruno Mijail Díaz Barba. All rights reserved.

The original application software is proprietary; see [LICENSE](LICENSE) and
[NOTICE](NOTICE). No public or open-source license is granted. Dependencies
and third-party assets retain their own licenses and owners' rights.

The platform was developed for the FlagTastic Football League. The League is
completing its legal incorporation, and a separate written software license
agreement remains to be formalized with the appropriate contracting party.
These repository notices do not transfer ownership or state that an agreement
has already been signed. Software rights are distinct from League branding,
uploaded content, sports records, and personal data.
