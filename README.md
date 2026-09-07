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

The project structure currently includes a lightweight frontend foundation using:

- HTML
- CSS
- Vanilla JavaScript

More frontend functionality will be added as the backend domain stabilizes.

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
│   ├── teams.py
│   └── players.py
│
├── repositories/
│   ├── __init__.py
│   ├── teams.py
│   └── players.py
│
├── templates/
│   └── index.html
│
├── static/
│   ├── app.js
│   └── styles.css
│
└── tests/
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

The default development connection is:

```text
postgresql://flagtastic:flagtastic@localhost:5432/flagtastic
```

The connection can be overridden using the `DATABASE_URL` environment variable.

Example:

```env
DATABASE_URL=postgresql://flagtastic:flagtastic@localhost:5432/flagtastic
```

---

# ▶️ Running the API

Start the FastAPI development server:

```powershell
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

Run the test suite:

```powershell
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
docker run --rm -p 8000:8000 -e DATABASE_URL="postgresql://flagtastic:flagtastic@host.docker.internal:5432/flagtastic" flagtastic-league
```

Health check:

```powershell
curl http://localhost:8000/live
```
---

## CI

GitHub Actions runs the test suite on every push and pull request.

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
    E[Player Game Stats]
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
player_game_stats
```

---

# 📊 Planned Player Statistics

Player statistics will be recorded **per game** rather than stored only as lifetime totals.

This will allow Flagtastic to calculate statistics by:

- Game
- Season
- Team
- Player
- Category
- Branch

Planned statistics include:

| Statistic | Description |
|---|---|
| Pass completions | Completed passes |
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

# 🏆 Planned Leaderboards

Accumulated game statistics will power league leaderboards.

| Statistic | Leaderboard |
|---|---|
| Pass completions | 🎯 El Francotirador |
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

# 🔐 Planned Roles

Future versions of Flagtastic are expected to include authentication and authorization.

Possible roles include:

```text
League Administrator
Team Administrator
Statistics Operator
Public User
```

Administrative functionality will have access to private player information when required.

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
```

Current focus:

```text
🚧 Player eligibility rules
```

Coming next:

```text
⬜ Games
⬜ Per-game statistics
⬜ Season statistics
⬜ Leaderboards
⬜ Authentication
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