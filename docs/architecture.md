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
    Models[Pydantic Models]
    Repositories[Repositories]
    DB[(PostgreSQL)]
    Tests[pytest + TestClient]

    Client --> App
    Static --> Client
    App --> Routes
    Routes --> Models
    Routes --> Repositories
    Repositories --> DB
    Tests --> App
    Tests --> DB
```

The application starts in `main.py`. During startup, it creates the FastAPI instance, runs table bootstrap through `create_database()`, and registers the teams, players, and games routers.

## Layers

### Application

Main file: `main.py`

Responsibilities:

- Create the FastAPI instance.
- Register routers.
- Expose the `GET /live` health check.
- Run initial table creation.

### Contracts

Main file: `models.py`

Responsibilities:

- Define Pydantic models that validate incoming payloads.
- Keep basic shape and range validation close to the API boundary.

Current models:

- `TeamCreate`: name, branch, and category.
- `PlayerCreate`: name, CURP, age, and jersey number.
- `GameCreate`: home team and away team.

### HTTP Routes

Main folder: `routes/`

Responsibilities:

- Define public API endpoints.
- Translate domain or persistence errors into HTTP responses.
- Validate request flow rules that depend on existing resources.
- Delegate data operations to repositories.

Current routers:

- `routes/teams.py`: team registration and listing.
- `routes/players.py`: player registration and roster listing by team.
- `routes/games.py`: game creation and listing.

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

### Database

Main file: `database.py`

Responsibilities:

- Resolve `DATABASE_URL`.
- Create psycopg connections using `dict_row`.
- Create required tables if they do not already exist.

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
```

### Modeling Decisions

A person's identity is separated from their participation in teams.

- `players` represents the person.
- `teams` represents a team registered in a branch and category.
- `team_players` represents a person's membership in a team.
- `games` represents a matchup between two teams.

This separation allows the same person to play for multiple teams when league eligibility rules allow it.

## Domain Rules

### Teams

- Every team has `name`, `branch`, `category`, and `status`.
- New teams are created with `status = "pending"`.

### Players

- CURP uniquely identifies a person.
- The public roster does not expose CURP.
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
| `POST` | `/api/teams` | Creates a team |
| `GET` | `/api/teams` | Lists teams |
| `POST` | `/api/teams/{team_id}/players` | Registers a player in a team |
| `GET` | `/api/teams/{team_id}/players` | Lists a team's roster |
| `POST` | `/api/games` | Creates a game |
| `GET` | `/api/games` | Lists games |

## Frontend

The frontend foundation lives in:

- `templates/index.html`
- `static/style.css`
- `static/app.js`

It is currently a lightweight HTML, CSS, and JavaScript layer. The backend remains API-first, so the frontend can evolve without coupling directly to persistence.

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

Tests clean the database between cases to preserve isolation.

## Configuration and Deployment

The application reads the connection string from `DATABASE_URL`.

Default local value:

```text
postgresql://flagtastic:flagtastic@localhost:5432/flagtastic
```

The `Dockerfile` builds an image based on `python:3.14-slim`, installs dependencies from `requirements.txt`, copies the project, and starts Uvicorn on `0.0.0.0:8000`.

Application command:

```text
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Delivery Architecture

GitHub Actions runs the delivery checks on every push and pull request.

The current pipeline validates:

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

As domain rules grow, the natural next step is to introduce a service or domain layer between routes and repositories. That layer could centralize eligibility rules, scheduling, statistics capture, standings calculations, and administrative permissions.

## Current Conventions

- Routes handle HTTP responses and client-visible errors.
- Repositories are responsible for SQL and transactions.
- Pydantic models validate incoming payloads.
- The database keeps constraints that should not depend only on application code.
- Public responses avoid exposing CURP in rosters.

## Risks and Considerations

- Table creation currently happens when the app starts; production should use a migration tool before the first real deployment.
- Domain rules are partially split between routes and repositories; if they grow, extracting services would help.
- Authentication and authorization do not exist yet.
- CURP privacy must remain explicit as administrative and public endpoints are added.
- Per-game statistics are not modeled yet.
