# 🏈 Flagtastic

**Flagtastic** is a football league management platform built for the **Flagtastic Football League**.

The project is designed to provide a reliable foundation for managing teams, player rosters, eligibility rules, games, player statistics, and league-wide leaderboards.

The backend is currently being built with **FastAPI**, **PostgreSQL**, and **pytest**, following an API-first approach with a simple architecture that can evolve as the application grows.

---

## ✨ Current Features

### Teams

Teams can be registered with:

- Name
- Branch
- Category
- Status

Available endpoints:

```http
POST /api/teams
GET /api/teams
```

Example team:

```json
{
  "name": "Tigres",
  "branch": "varonil",
  "category": "libre"
}
```

---

### Player Rosters

Players can be registered to a team using:

- Name
- CURP
- Age
- Jersey number

Available endpoints:

```http
POST /api/teams/{team_id}/players
GET /api/teams/{team_id}/players
```

Player identity and team membership are modeled separately.

This allows the same person to participate in multiple teams when league eligibility rules allow it.

CURP is used internally to uniquely identify a person and is not exposed in public roster responses.

---

### Health Check

```http
GET /live
```

Example response:

```json
{
  "status": "alive"
}
```

---

# 🧠 Player Eligibility Rules

A player may participate in multiple teams across different branch/category combinations.

For example:

```text
Carlos López → Tigres / Varonil / Libre     ✅
Carlos López → Ravens / Mixto / Libre       ✅
Carlos López → Nómadas / Varonil / U18      ✅
Carlos López → Nómadas / Varonil / U16      ✅
```

However, a player cannot participate in two different teams inside the **same branch and category**.

```text
Carlos López → Tigres / Varonil / Libre     ✅
Carlos López → Halcones / Varonil / Libre   ❌
```

Jersey numbers only need to be unique inside each team.

```text
Tigres  → Player #83   ✅
Ravens  → Player #83   ✅
```

The same jersey number may therefore exist across different teams.

---

# 🗄️ Data Model

Player identity is separated from team membership.

This is important because a person is not inherently tied to a single team.

```mermaid
erDiagram

    TEAMS ||--o{ TEAM_PLAYERS : has
    PLAYERS ||--o{ TEAM_PLAYERS : joins

    TEAMS {
        int id PK
        string name
        string branch
        string category
        string status
    }

    PLAYERS {
        int id PK
        string name
        string curp UK
        int age
    }

    TEAM_PLAYERS {
        int id PK
        int team_id FK
        int player_id FK
        int jersey_number
    }
```

The membership table enforces:

```text
UNIQUE(team_id, player_id)
UNIQUE(team_id, jersey_number)
```

These constraints guarantee that:

- The same player cannot appear twice in the same team.
- Two players cannot use the same jersey number inside the same team.

League-level eligibility rules, such as preventing the same player from joining two teams in the same branch and category, are validated by the application.

---

# 🏗️ Architecture

Flagtastic currently follows a lightweight layered architecture.

```mermaid
flowchart TD

    A[Client / Frontend]
    B[FastAPI Routes]
    C[Repository Layer]
    D[(PostgreSQL)]
    E[Pydantic Models]
    F[Business Rules]

    A --> B
    B --> E
    B --> C
    C --> F
    C --> D

    D --> G[teams]
    D --> H[players]
    D --> I[team_players]
```

The current request flow is:

```text
HTTP Request
     ↓
FastAPI Route
     ↓
Repository
     ↓
PostgreSQL
```

As the project grows, more complex business rules may be moved into a dedicated service or domain layer.

The current priority is keeping the architecture understandable while the league domain is being modeled.

---

# ⚙️ Tech Stack

### Backend

- Python
- FastAPI
- Pydantic
- Psycopg

### Database

- PostgreSQL

### Testing

- pytest
- FastAPI TestClient

### Infrastructure

- Docker

### Frontend

The project includes a lightweight server-rendered frontend using:

- Jinja templates
- CSS
- Vanilla JavaScript

The frontend is split into page templates. Shared layout lives in `templates/base.html`, while each page loads only the JavaScript it needs.

On screens up to `820px`, the sidebar becomes an accessible overlay drawer and all forms and card grids use a single-column layout. Wide data tables remain readable through contained horizontal scrolling instead of widening the whole page. Mobile changes should be checked at `360px`, `390px`, and `430px` before release.

---

# 📁 Project Structure

```text
flagtastic-league/
├── main.py
├── database.py
├── models.py
├── requirements.txt
├── pytest.ini
│
├── routes/
│   ├── __init__.py
│   ├── auth.py
│   ├── games.py
│   ├── standings.py
│   ├── statistics.py
│   ├── teams.py
│   └── players.py
│
├── repositories/
│   ├── __init__.py
│   ├── games.py
│   ├── standings.py
│   ├── teams.py
│   └── players.py
│
├── templates/
│   ├── base.html
│   ├── games.html
│   ├── login.html
│   ├── roster.html
│   ├── statistics.html
│   ├── standings.html
│   └── teams.html
│
├── static/
│   ├── api.js
│   ├── games.js
│   ├── layout.js
│   ├── standings.js
│   ├── statistics.js
│   ├── login.js
│   ├── roster.js
│   ├── style.css
│   └── teams.js
│
└── tests/
    ├── test_games.py
    ├── test_standings.py
    ├── test_teams.py
    └── test_player.py
```

---

# 🚀 Local Development

## 1. Clone the repository

```bash
git clone <repository-url>
cd flagtastic-league
```

---

## 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

---

## 3. Install dependencies

```powershell
pip install -r requirements.txt
```

---

# 🐘 PostgreSQL

The project can run PostgreSQL locally using Docker.

```powershell
docker run -d `
    --name flagtastic-postgres `
    -e POSTGRES_USER=flagtastic `
    -e POSTGRES_PASSWORD=flagtastic `
    -e POSTGRES_DB=flagtastic `
    -p 5432:5432 `
    -v flagtastic-postgres-data:/var/lib/postgresql/data `
    postgres:17
```

The local development connection used in the examples is:

```text
postgresql://flagtastic:flagtastic@localhost:5432/flagtastic
```

`DATABASE_URL` is required. The application and Alembic fail explicitly when it is not configured. Local development values are documented in `.env.example`; CI and deployed environments provide the value through environment configuration or secrets.

Example:

```powershell
$env:DATABASE_URL="postgresql://flagtastic:flagtastic@localhost:5432/flagtastic"
```

---

# ▶️ Running the API

Apply all pending database migrations before starting the FastAPI development server:

```powershell
$env:DATABASE_URL="postgresql://flagtastic:flagtastic@localhost:5432/flagtastic"
python -m alembic upgrade head
uvicorn main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

FastAPI automatically provides interactive API documentation.

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

---

# 🧪 Testing

Flagtastic uses a separate PostgreSQL database for automated tests.

Create it with:

```powershell
docker exec flagtastic-postgres `
    psql -U flagtastic -d postgres `
    -c "CREATE DATABASE flagtastic_test;"
```

The test environment uses:

```text
postgresql://flagtastic:flagtastic@localhost:5432/flagtastic_test
```

Configure and migrate the test database, then run the test suite. The test
configuration reads `TEST_DATABASE_URL` locally and will not reuse the
development `DATABASE_URL`:

```powershell
$env:TEST_DATABASE_URL="postgresql://flagtastic:flagtastic@localhost:5432/flagtastic_test"
$env:DATABASE_URL=$env:TEST_DATABASE_URL
python -m alembic upgrade head
pytest -v
```

Tests currently cover core behavior including:

- Team registration
- Team listing
- Player registration
- Team roster retrieval
- Registration against nonexistent teams
- Duplicate jersey protection

Additional eligibility tests will be added as the domain rules are expanded.

---

## Docker

Build the image:

```powershell
docker build -t flagtastic-league .
```

Run the app:

```powershell
docker volume create flagtastic-profile-photos

docker run --rm -p 8000:8000 `
    -e DATABASE_URL="postgresql://flagtastic:flagtastic@host.docker.internal:5432/flagtastic" `
    flagtastic-league
```

Profile photos are stored in PostgreSQL so they survive replacement of a
container or serverless function. Production must leave
`SESSION_COOKIE_SECURE=true` and serve the application through HTTPS.

Health check:

```powershell
curl http://localhost:8000/live
```
---

## CI

GitHub Actions applies all Alembic migrations to a clean PostgreSQL service and then runs the test suite on every push and pull request.

The workflow uses a PostgreSQL service container and requires these repository secrets:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
---

# 🗺️ Development Roadmap

```mermaid
flowchart LR

    A[Teams]
    B[Player Rosters]
    C[Eligibility Rules]
    D[Games]
    E[Player Week Stats]
    F[Season Stats]
    G[Leaderboards]
    H[Authentication & Roles]
    I[Deployment]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
```

---

# 🎮 Planned Game Management

The next major domain entity will be games.

A game will eventually represent information such as:

```text
Tigres 32 - Ravens 24
```

and connect participating teams with individual player performances.

Future entities are expected to include:

```text
seasons
categories
teams
players
team_players
games
player_week_stats
```

---

# 📊 Player Statistics

Player statistics are recorded **per jornada** rather than stored only as lifetime totals. The official multi-sheet Excel workbook can import every `Wk` sheet in one operation.

This will allow Flagtastic to calculate statistics by:

- Jornada
- Season
- Team
- Player
- Category
- Branch

The workbook identifies each roster entry with `rama`, `categoria`, `equipo`, and `numero`. The application resolves the internal player ID and displays the roster name; names are never trusted from the spreadsheet.

Each pair of consecutive 15-row team blocks represents one matchup. Scores are inferred from `TD`, `Conv 1`, and `Conv 2`; when the event-only source omits enough information to produce a tie, defensive events provide a deterministic one-point tiebreak because league games cannot end tied. Formula-helper columns are ignored so events are not counted twice.

The games page filters the imported schedule by jornada, branch, and category.
For visual testing of standings, development schedules can be equalized without
changing existing results:

```powershell
python -m scripts.balance_mock_games
```

The command inserts deterministic, non-tied mock games in a new jornada until
every team in each active division has the same number of completed games. It
is idempotent, so running it again after balance is reached creates nothing.

Statistics include:

| Statistic | Description |
|---|---|
| Pass completion | Completion percentage (completed / attempted) |
| Receptions | Successful receptions |
| Points | Points scored |
| Tackles | Defensive stops |
| Interceptions | Passes intercepted |
| Sacks | Quarterback sacks |

Example player performance:

```text
Bruno Díaz #83

Receptions:     4
Points:        12
Tackles:        3
Interceptions:  1
```

---

# 🏆 Leaderboards

Accumulated game statistics will power league leaderboards.

| Statistic | Leaderboard |
|---|---|
| Pass completion | 🎯 El Francotirador |
| Receptions | 👐 Manos de Acero |
| Points | ⚡ Máquina de Puntos |
| Tackles | 🧱 El Muro |
| Interceptions | 🦅 Cazador Aéreo |
| Sacks | 💥 Cazador de QBs |

Leaderboards will eventually support filtering by:

```text
Season
Branch
Category
Team
```

---

# 🔐 Authentication and Roles

Flagtastic supports credential authentication backed by database sessions. Login creates a random session token, stores only its SHA-256 hash, and sends the raw token in an `HttpOnly`, `SameSite=Lax` cookie. Production cookies are `Secure` by default.

Current account roles are:

```text
League Administrator
Team Representative
Player
Referee
```

Roles are cumulative. One account may simultaneously be a player, league
administrator, team representative, and referee. `user_roles` is the source of
truth for authorization; the older `users.role` value remains only for
compatibility with existing integrations. Granting an operational role never
removes the player's identity or personal dashboard.

League administrators assign officials to games from `/games`. Each assignment
has one position: Referee, Down Judge, Field Judge, Side Judge, or Statistician,
and records the administrator who made it and its timestamp. Referee and Down
Judge are required when confirming a complete imported role; the other slots
remain optional for U6, regular games, and finals. Referees use
`/referee/games` to see only their own schedule; the backend enforces that
scope even if somebody calls the API directly.

League administrators can also create operational staff accounts from
`/admin/users`. These accounts receive one or more non-player roles and do not
require CURP, age, roster membership, or a profile photo. This supports league
staff such as a president who is both an administrator and a referee.
Administrator-created accounts must replace their initial password at first
login before any protected operation becomes available.

Administrators can upload the official referee role as a JPG, PNG, or WebP
image from `/referee/games`. Local OCR proposes matching games, fields, and
active referee accounts. The recognized text and every proposal remain
editable; no official record changes until an administrator confirms the
review table.

Every newly scheduled game identifies a field from 1 through 8. Public game
cards and private referee schedules show that field so teams and officials use
the same assignment. Historical workbook imports may temporarily display
`Campo por asignar` until the official referee schedule supplies it.

Player self-registration requires a JPG, PNG, or WebP profile photo of at most
5 MB and accepts an optional `AKA`. PostgreSQL stores the validated image bytes,
media type, and generated public filename so profile media remains available
on stateless deployments. Players, including accounts created before AKA support,
can edit it from the personal dashboard. Public navigation and official roles
prefer the AKA while administration retains the legal name as supporting identity.

`/teams` is the searchable team directory. Selecting a team opens its dedicated
`/teams/{team_id}/roster` page instead of expanding roster management inside the
directory. Public roster entries and individual-statistics leaderboards show the
profile photo and prefer the player's AKA as the display name while retaining the
legal roster name as supporting identity. Existing players without a photo use an
initials placeholder, so imported and historical data remains readable.

The authentication API supports login, current-user lookup, and idempotent logout. Backend authorization restricts league-wide writes to administrators and roster writes to administrators or representatives assigned to that team.

Only league administrators can delete an erroneous team from `/teams`. This is
a cascading operation: its roster memberships, games, representative links,
and statistics are removed with the team, so the interface requires explicit
confirmation before sending the request.

Create the first trusted administrator locally after applying migrations:

```powershell
python -m scripts.create_admin --email admin@flagtastic.com --name "League Admin"
```

If that email already belongs to a registered player or representative, the
command preserves the existing password and identity and promotes the account
instead of creating a duplicate.

That administrator can open `/admin/users` and grant any combination of
`league_admin`, `team_representative`, `player`, and `referee`. The `player`
role requires an account already linked to a player identity. Administrators
cannot remove their own admin role accidentally.

Administrative functionality will have access to private player information only when required by its role.

Public endpoints will expose only information appropriate for league participants and spectators.

---

# 🔒 Privacy

Player CURP is considered administrative information.

It is used to identify the same person across multiple team registrations but should not be exposed through public roster endpoints.

Conceptually:

```text
Administrative Player Data
├── Name
├── CURP
├── Age
└── Memberships

Public Roster
├── Name
├── Age
└── Jersey Number
```

---

# 🎯 MVP Goal

The first Flagtastic MVP aims to provide the league with a reliable system for:

```text
Team Registration
        ↓
Roster Management
        ↓
Eligibility Validation
        ↓
Game Registration
        ↓
Player Statistics
        ↓
League Leaderboards
```

The goal is to build the domain correctly first and expand the platform incrementally instead of introducing unnecessary complexity early in development.

---

# 📌 Project Status

**Flagtastic is currently under active development.**

Completed foundation:

```text
✅ FastAPI project structure
✅ PostgreSQL integration
✅ Team registration
✅ Team listing
✅ Player registration
✅ Team rosters
✅ Player / team membership separation
✅ Duplicate jersey protection
✅ Automated tests
✅ Secure session authentication and role-based authorization
✅ Player self-registration and personal dashboard
✅ Excel statistics imports and top-five leaderboards
✅ Passing completion leaderboard with jornada qualification rules
✅ Referee schedule image review and per-game official assignments
✅ Role-scoped game details and per-game statistics
✅ Administrator replacement of last-minute officiating assignments
```

Current focus:

```text
🚧 Public-release stabilization
```

## Local demo data

The official multi-jornada workbook can prepare a complete local dataset with:

```powershell
python -m scripts.seed_statistics_workbook "C:\path\to\Stats ALL.xlsx"
```

The command is idempotent: it creates only missing teams and mock roster
members, then imports games and game-scoped player statistics. Matching games
are reused so their field, time, and officiating assignments are preserved.
Run `python -m alembic upgrade head` before importing a workbook.

Coming next:

```text
✅ Games
✅ Per-game statistics
✅ Aggregated player statistics
✅ Leaderboards
✅ Role-based authorization
⬜ Deployment
```

---

# 🏈 Flagtastic Football League

Flagtastic is being developed as a real-world league management platform for the **Flagtastic Football League**.

The project prioritizes:

- Clear domain modeling
- Data integrity
- Testable business rules
- Simple architecture
- Incremental development
- Long-term maintainability

---

## License

This project is currently developed for the **Flagtastic Football League**.
