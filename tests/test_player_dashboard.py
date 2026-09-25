"""End-to-end tests for player registration and the personal dashboard."""

from fastapi.testclient import TestClient

from database import get_connection
from main import app


client = TestClient(app, base_url="https://testserver")
PROFILE_PNG = b"\x89PNG\r\n\x1a\nprofile-test"


def register_player(**overrides):
    """Submit the multipart registration contract used by the browser."""
    data = {
        "email": "player@example.com",
        "password": "supersecret",
        "name": "Bruno Diaz",
        "aka": "El Muro",
        "curp": "DIBB961215HASXXX00",
        "age": "29"
    }
    data.update(overrides)
    return client.post(
        "/api/auth/register/player",
        data=data,
        files={"photo": ("profile.png", PROFILE_PNG, "image/png")}
    )


def _clean_database():
    connection = get_connection()
    connection.execute("DELETE FROM sessions")
    connection.execute("DELETE FROM player_week_stats")
    connection.execute("DELETE FROM games")
    connection.execute("DELETE FROM team_players")
    connection.execute("DELETE FROM team_representatives")
    connection.execute("DELETE FROM users")
    connection.execute("DELETE FROM players")
    connection.execute("DELETE FROM teams")
    connection.commit()
    connection.close()


def setup_function():
    client.cookies.clear()
    _clean_database()


def test_player_registers_joins_team_and_reads_dashboard():
    team = client.post(
        "/api/teams",
        json={"name": "Tigres", "branch": "varonil", "category": "libre"}
    ).json()
    registration = register_player()
    assert registration.status_code == 201
    assert registration.json()["role"] == "player"
    assert "password" not in registration.text
    assert "curp" not in registration.text.lower()

    login = client.post(
        "/api/auth/login",
        json={"email": "player@example.com", "password": "supersecret"}
    )
    assert login.status_code == 200

    joined = client.post(
        f"/api/me/teams/{team['id']}",
        json={"jersey_number": 83}
    )
    assert joined.status_code == 201

    roster = client.get(f"/api/teams/{team['id']}").json()["players"]
    assert roster[0]["aka"] == "El Muro"
    assert roster[0]["profile_photo_url"].startswith("/media/profiles/")

    dashboard = client.get("/api/me/dashboard")
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["player"]["name"] == "Bruno Diaz"
    assert body["player"]["aka"] == "El Muro"
    assert body["player"]["profile_photo_url"].startswith("/media/profiles/")
    photo = client.get(body["player"]["profile_photo_url"])
    assert photo.status_code == 200
    assert photo.content == PROFILE_PNG
    assert body["teams"][0]["team_name"] == "Tigres"
    assert body["teams"][0]["standing_position"] == 1
    assert body["statistics"]["passes_attempted"] == 0


def test_player_cannot_join_two_teams_in_same_division():
    first = client.post(
        "/api/teams",
        json={"name": "Tigres", "branch": "varonil", "category": "libre"}
    ).json()
    second = client.post(
        "/api/teams",
        json={"name": "Ravens", "branch": "varonil", "category": "libre"}
    ).json()
    register_player(aka="")
    client.post(
        "/api/auth/login",
        json={"email": "player@example.com", "password": "supersecret"}
    )
    assert client.post(
        f"/api/me/teams/{first['id']}", json={"jersey_number": 83}
    ).status_code == 201
    conflict = client.post(
        f"/api/me/teams/{second['id']}", json={"jersey_number": 12}
    )
    assert conflict.status_code == 409


def test_player_registration_requires_a_valid_profile_photo():
    missing = client.post(
        "/api/auth/register/player",
        data={
            "email": "player@example.com", "password": "supersecret",
            "name": "Bruno Diaz", "curp": "DIBB961215HASXXX00", "age": "29"
        }
    )
    assert missing.status_code == 422

    invalid = client.post(
        "/api/auth/register/player",
        data={
            "email": "player@example.com", "password": "supersecret",
            "name": "Bruno Diaz", "curp": "DIBB961215HASXXX00", "age": "29"
        },
        files={"photo": ("profile.png", b"not-an-image", "image/png")}
    )
    assert invalid.status_code == 415
    assert invalid.json()["detail"] == "La foto debe ser JPG, PNG o WebP"
