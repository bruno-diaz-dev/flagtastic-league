"""Release smoke test covering the complete least-privilege user journey."""

from uuid import uuid4

from fastapi.testclient import TestClient

from database import get_connection
from main import app
from models import UserCreate
from repositories.users import create_user


client = TestClient(app, base_url="https://testserver")
PROFILE_PNG = b"\x89PNG\r\n\x1a\nrelease-smoke-profile"


def reset_test_database():
    """Reset only the dedicated test database used by pytest."""
    connection = get_connection()
    for table in (
        "game_referees", "sessions", "player_week_stats", "games",
        "team_players", "team_representatives", "user_roles", "users",
        "players", "teams"
    ):
        connection.execute(f"DELETE FROM {table}")
    connection.commit()
    connection.close()


def login(email, password="supersecret"):
    """Start a fresh browser-like session for one role."""
    client.cookies.clear()
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )


def test_complete_release_flow_for_public_and_all_roles():
    """Exercise the launch-critical flow from account setup to public results."""
    app.dependency_overrides.clear()
    client.cookies.clear()
    reset_test_database()
    suffix = uuid4().hex[:8]

    admin_email = f"admin-{suffix}@example.test"
    representative_email = f"representative-{suffix}@example.test"
    create_user(UserCreate(
        email=admin_email,
        name="League Admin",
        password="supersecret",
        role="league_admin"
    ))
    representative = create_user(UserCreate(
        email=representative_email,
        name="Team Representative",
        password="supersecret",
        role="team_representative"
    ))

    # A representative can create a team and is assigned to it automatically.
    assert login(representative_email).status_code == 200
    home_response = client.post(
        "/api/teams",
        json={
            "name": f"Smoke Home {suffix}",
            "branch": "mixto",
            "category": "libre"
        }
    )
    assert home_response.status_code == 201
    home_team = home_response.json()
    assert client.get("/api/admin/users").status_code == 403

    # A player creates an account with public identity media and joins the team.
    player_email = f"player-{suffix}@example.test"
    client.cookies.clear()
    registration = client.post(
        "/api/auth/register/player",
        data={
            "email": player_email,
            "password": "supersecret",
            "name": "Release Player",
            "aka": "Smoke Star",
            "curp": f"SMOKE{suffix.upper()}00000"[:18],
            "age": "24"
        },
        files={"photo": ("profile.png", PROFILE_PNG, "image/png")}
    )
    assert registration.status_code == 201
    assert login(player_email).status_code == 200
    assert client.post(
        f"/api/me/teams/{home_team['id']}",
        json={"jersey_number": 7}
    ).status_code == 201
    assert client.post(
        "/api/teams",
        json={"name": "Forbidden", "branch": "mixto", "category": "libre"}
    ).status_code == 403

    dashboard = client.get("/api/me/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["player"]["aka"] == "Smoke Star"

    # The administrator performs league-wide operations and records a result.
    assert login(admin_email).status_code == 200
    away_response = client.post(
        "/api/teams",
        json={
            "name": f"Smoke Away {suffix}",
            "branch": "mixto",
            "category": "libre"
        }
    )
    assert away_response.status_code == 201
    away_team = away_response.json()
    game_response = client.post(
        "/api/games",
        json={
            "home_team_id": home_team["id"],
            "away_team_id": away_team["id"],
            "week": 1,
            "field_number": 3
        }
    )
    assert game_response.status_code == 201
    game = game_response.json()
    assert client.patch(
        f"/api/games/{game['id']}/score",
        json={"home_score": 28, "away_score": 20}
    ).status_code == 200
    users = client.get("/api/admin/users")
    assert users.status_code == 200
    assert {user["id"] for user in users.json()} >= {representative["id"]}
    assert "password" not in users.text.lower()

    # Public visitors can read the launch-critical pages and resulting data.
    client.cookies.clear()
    roster = client.get(f"/api/teams/{home_team['id']}")
    assert roster.status_code == 200
    assert roster.json()["players"][0]["aka"] == "Smoke Star"
    assert roster.json()["players"][0]["profile_photo_url"]
    assert client.get("/api/games").status_code == 200
    standings = client.get(
        "/api/standings", params={"branch": "mixto", "category": "libre"}
    )
    assert standings.status_code == 200
    assert standings.json()[0]["team_id"] == home_team["id"]
    for path in (
        "/teams", f"/teams/{home_team['id']}/roster", "/games",
        "/standings", "/statistics"
    ):
        assert client.get(path).status_code == 200
