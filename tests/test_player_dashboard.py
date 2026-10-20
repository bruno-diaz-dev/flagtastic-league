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
    connection.execute("DELETE FROM game_referees")
    connection.execute("DELETE FROM sessions")
    connection.execute("DELETE FROM player_week_stats")
    connection.execute("DELETE FROM games")
    connection.execute("DELETE FROM team_players")
    connection.execute("DELETE FROM team_representatives")
    connection.execute("DELETE FROM user_roles")
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
    assert photo.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert photo.headers["cdn-cache-control"] == "public, max-age=31536000"
    assert photo.headers["vercel-cdn-cache-control"] == "public, max-age=31536000"
    assert photo.status_code == 200
    assert photo.content == PROFILE_PNG
    assert body["teams"][0]["team_name"] == "Tigres"
    assert body["teams"][0]["standing_position"] == 1
    assert body["statistics"]["passes_attempted"] == 0

    public_profile = client.get(
        f"/api/players/{registration.json()['player_id']}/profile"
    )
    assert public_profile.status_code == 200
    assert public_profile.json()["player"]["aka"] == "El Muro"
    assert public_profile.json()["teams"][0]["team_name"] == "Tigres"
    assert "curp" not in public_profile.text.lower()
    assert "email" not in public_profile.text.lower()


def test_player_claims_representative_created_roster_identity():
    """Account registration enriches the roster row instead of duplicating it."""
    team = client.post(
        "/api/teams",
        json={"name": "Tigres", "branch": "varonil", "category": "libre"}
    ).json()
    roster_player = client.post(
        f"/api/teams/{team['id']}/players",
        json={
            "name": "Bruno Diaz",
            "curp": "dibb961215hasxxx00",
            "age": 29,
            "jersey_number": 83
        }
    ).json()

    registration = register_player()

    assert registration.status_code == 201
    assert registration.json()["player_id"] == roster_player["id"]
    roster = client.get(f"/api/teams/{team['id']}").json()["players"]
    assert len(roster) == 1
    assert roster[0]["id"] == roster_player["id"]
    assert roster[0]["jersey_number"] == 83
    assert roster[0]["aka"] == "El Muro"
    assert roster[0]["profile_photo_url"].startswith("/media/profiles/")


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


def test_existing_player_can_update_public_aka():
    register_player(aka="")
    client.post(
        "/api/auth/login",
        json={"email": "player@example.com", "password": "supersecret"}
    )

    updated = client.patch("/api/me/profile", json={"aka": "Brucie"})

    assert updated.status_code == 200
    assert updated.json()["aka"] == "Brucie"
    assert client.get("/api/auth/me").json()["display_name"] == "Brucie"
    assert client.get("/api/me/dashboard").json()["player"]["aka"] == "Brucie"


def test_profile_categories_do_not_mix_stats_or_count_games_as_extra_weeks():
    teams = []
    for category in ('u10', 'u12'):
        teams.append(client.post('/api/teams', json={'name': f'Team {category}', 'branch': 'mixto', 'category': category}).json())
    registration = register_player()
    player_id = registration.json()['player_id']
    assert client.post('/api/auth/login', json={'email': 'player@example.com', 'password': 'supersecret'}).status_code == 200
    for team in teams:
        assert client.post(f"/api/me/teams/{team['id']}", json={'jersey_number': 5}).status_code == 201
    connection = get_connection()
    # Five player/game records, including a U10 doubleheader, span two actual weeks.
    for team_index, week, points, interceptions in [(0, 1, 6, 1), (0, 1, 0, 0), (0, 2, 0, 0),
                                                    (1, 1, 12, 1), (1, 2, 6, 0)]:
        team = teams[team_index]
        rival = connection.execute("INSERT INTO teams (name,branch,category,status) VALUES (%s,'mixto',%s,'active') RETURNING id", (f'Rival {team_index} {week} {points}', team['category'])).fetchone()['id']
        game = connection.execute("INSERT INTO games (home_team_id,away_team_id,week,status,home_score,away_score) VALUES (%s,%s,%s,'completed',6,0) RETURNING id", (team['id'], rival, week)).fetchone()['id']
        connection.execute("INSERT INTO player_week_stats (week,game_id,player_id,team_id,points,interceptions,passes_completed,passes_attempted) VALUES (%s,%s,%s,%s,%s,%s,1,%s)", (week, game, player_id, team['id'], points, interceptions, 2 if team_index == 0 else 1))
    connection.commit()
    connection.close()
    for team in teams:
        params = f"?team_id={team['id']}"
        statistics = client.get(f'/api/players/{player_id}/stats{params}').json()
        assert statistics['interceptions'] == 1
        assert statistics['weeks'] == 2
        assert statistics['team_id'] == team['id']
        assert statistics['points'] == (6 if team['category'] == 'u10' else 18)
        assert statistics['completion_percentage'] == (50 if team['category'] == 'u10' else 100)
        public = client.get(f'/api/players/{player_id}/profile{params}').json()
        personal = client.get('/api/me/dashboard'+params).json()
        for profile in (public, personal):
            assert profile['selected_team_id'] == team['id']
            assert profile['statistics']['interceptions'] == 1
            assert profile['statistics']['weeks'] == 2
            assert len(profile['teams']) == 2
            assert all(scope['statistics']['interceptions'] == 1 for scope in profile['teams'])
        leaders = client.get(f"/api/statistics/leaderboards?branch=mixto&category={team['category']}").json()
        assert leaders['interceptions'][0]['player_id'] == player_id
        assert leaders['interceptions'][0]['value'] == 1
    default = client.get(f'/api/players/{player_id}/profile').json()
    assert default['statistics']['interceptions'] == 1
    assert default['statistics']['weeks'] == 2
    for endpoint in (f'/api/players/{player_id}/stats', f'/api/players/{player_id}/profile', '/api/me/dashboard'):
        assert client.get(endpoint+'?team_id=999999').status_code == 404
        assert client.get(endpoint+'?team_id=0').status_code == 422
