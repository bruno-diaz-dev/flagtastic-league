import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://flagtastic:flagtastic@localhost:5432/flagtastic"
)

from database import get_connection
from main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_database():
    connection = get_connection()

    connection.execute("DELETE FROM team_players")
    connection.execute("DELETE FROM players")
    connection.execute("DELETE FROM teams")

    connection.commit()
    connection.close()

def create_test_team(
    name="Tigres",
    branch="varonil",
    category="libre"
):
    response = client.post(
        "/api/teams",
        json={
            "name": name,
            "branch": branch,
            "category": category
        }
    )

    return response.json()["id"]

def test_create_game():
    tigres_id = create_test_team(
        name="Tigres"
    )

    ravens_id = create_test_team(
        name="Ravens"
    )

    response = client.post(
        "api/games",
        json={
            "home_team_id": tigres_id,
            "away_team_id": ravens_id,
            "field_number": 1
        }
    )

    assert response.status_code == 201
    
    data = response.json()

    assert "id" in data
    assert data["home_team_id"] == tigres_id
    assert data["away_team_id"] == ravens_id
    assert data["field_number"] == 1


@pytest.mark.parametrize("field_number", [0, 9])
def test_game_field_must_be_between_one_and_eight(field_number):
    tigres_id = create_test_team(name="Tigres")
    ravens_id = create_test_team(name="Ravens")

    response = client.post(
        "/api/games",
        json={
            "home_team_id": tigres_id,
            "away_team_id": ravens_id,
            "field_number": field_number
        }
    )

    assert response.status_code == 422

def test_team_cannot_play_against_itself():
    tigres_id = create_test_team(
        name="Tigres"
    )

    response = client.post(
        "/api/games",
        json={
            "home_team_id": tigres_id,
            "away_team_id": tigres_id,
            "field_number": 1
        }
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "A team cannot play against itself"
    }

def test_create_game_against_nonexistent_team():
    tigres_id = create_test_team(
        name="Tigres"
    )

    response = client.post(
        "/api/games",
        json={
            "home_team_id": tigres_id,
            "away_team_id": 9999,
            "field_number": 1
        }
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Team not found"
    }

def test_list_games():
    tigres_id = create_test_team(
        name="Tigres"
    )

    ravens_id = create_test_team(
        name="Ravens"
    )

    client.post(


        "/api/games",
        json={
            "home_team_id": tigres_id,
            "away_team_id": ravens_id,
            "field_number": 1
        }
    )

    response = client.get(
        "/api/games"
    )

    assert response.status_code == 200

    games = response.json()

    assert len(games) == 1
    assert games[0]["home_team_id"] == tigres_id
    assert games[0]["away_team_id"] == ravens_id


def test_list_games():
    tigres_id = create_test_team(
        name="Tigres"
    )

    ravens_id = create_test_team(
        name="Ravens"
    )

    create_response = client.post(
        "/api/games",
        json={
            "home_team_id": tigres_id,
            "away_team_id": ravens_id,
            "field_number": 2
        }
    )

    game_id = create_response.json()["id"]

    client.patch(
        f"/api/games/{game_id}/score",
        json={
            "home_score": 32,
            "away_score": 24
        }
    )

    response = client.get(
        "/api/games"
    )

    assert response.status_code == 200

    games = response.json()

    assert len(games) == 1

    assert games[0]["home_team"] == {
        "id": tigres_id,
        "name": "Tigres",
        "branch": "varonil",
        "category": "libre"
    }

    assert games[0]["away_team"] == {
        "id": ravens_id,
        "name": "Ravens",
        "branch": "varonil",
        "category": "libre"
    }

    assert games[0]["home_score"] == 32
    assert games[0]["away_score"] == 24
    assert games[0]["field_number"] == 2

def test_update_game_score():
    tigres_id = create_test_team(
        name="Tigres"
    )

    ravens_id = create_test_team(
        name="Ravens"
    )

    create_response = client.post(
        "/api/games",
        json={
            "home_team_id": tigres_id,
            "away_team_id": ravens_id,
            "field_number": 1
        }
    )

    game_id = create_response.json()["id"]

    response = client.patch(
        f"/api/games/{game_id}/score",
        json={
            "home_score": 32,
            "away_score": 24
        }
    )

    assert response.status_code == 200

    assert response.json() == {
        "id": game_id,
        "home_team_id": tigres_id,
        "away_team_id": ravens_id,
        "home_score": 32,
        "away_score": 24
    }

def test_update_game_score_not_found():
    response = client.patch(
        "/api/games/9999/score",
        json={
            "home_score": 32,
            "away_score": 24
        }
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Game not found"
    }

def test_game_score_cannot_be_tied():
    tigres_id = create_test_team(
        name="Tigres"
    )

    ravens_id = create_test_team(
        name="Ravens"
    )

    create_response = client.post(
        "/api/games",
        json={
            "home_team_id": tigres_id,
            "away_team_id": ravens_id,
            "field_number": 1
        }
    )

    game_id = create_response.json()["id"]

    response = client.patch(
        f"/api/games/{game_id}/score",
        json= {
            "home_score": 24,
            "away_score": 24
        }
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "A game cannot end in a tie"
    }


def test_reviewed_csv_schedule_creates_games_and_skips_repeat_uploads():
    tigres_id = create_test_team(name="Tigres")
    ravens_id = create_test_team(name="Ravens")
    content = b"jornada,campo,hora,local,visitante\n2,4,18:00,Tigres Var Libre,Ravens Var Libre\n"

    analysis = client.post(
        "/api/games/schedule/analyze",
        files={"file": ("rol.csv", content, "text/csv")},
    )

    assert analysis.status_code == 200
    proposal = analysis.json()["proposals"][0]
    assert proposal["home_team_id"] == tigres_id
    assert proposal["away_team_id"] == ravens_id
    payload = {"games": [{
        "home_team_id": proposal["home_team_id"],
        "away_team_id": proposal["away_team_id"],
        "week": proposal["week"],
        "field_number": proposal["field_number"],
        "start_time": proposal["start_time"],
    }]}

    first = client.post("/api/games/schedule/confirm", json=payload)
    repeated = client.post("/api/games/schedule/confirm", json=payload)

    assert first.json() == {"created": 1, "updated": 0, "skipped": 0}
    assert repeated.json() == {"created": 0, "updated": 0, "skipped": 1}
"""API tests for game scheduling, listing, and score updates."""


def test_reviewed_schedule_reimport_corrects_existing_slot():
    tigres_id = create_test_team(name="Tigres")
    ravens_id = create_test_team(name="Ravens")
    lobos_id = create_test_team(name="Lobos")

    first = client.post(
        "/api/games/schedule/confirm",
        json={"games": [{
            "home_team_id": tigres_id,
            "away_team_id": ravens_id,
            "week": 1,
            "field_number": 2,
            "start_time": "12:00",
        }]},
    )
    corrected = client.post(
        "/api/games/schedule/confirm",
        json={"games": [{
            "home_team_id": tigres_id,
            "away_team_id": lobos_id,
            "week": 1,
            "field_number": 2,
            "start_time": "12:00",
        }]},
    )

    assert first.json() == {"created": 1, "updated": 0, "skipped": 0}
    assert corrected.json() == {"created": 0, "updated": 1, "skipped": 0}

    games = client.get("/api/games").json()
    assert len(games) == 1
    assert games[0]["home_team"]["id"] == tigres_id
    assert games[0]["away_team"]["id"] == lobos_id


def test_schedule_cannot_replace_scored_game_and_rolls_back_batch():
    home = create_test_team(name="Home")
    away = create_test_team(name="Away")
    other = create_test_team(name="Other")
    row = dict(home_team_id=home, away_team_id=away, week=1,
               field_number=1, start_time="12:00")
    client.post("/api/games/schedule/confirm", json={"games": [row]})
    game_id = client.get("/api/games").json()[0]["id"]
    client.patch(f"/api/games/{game_id}/score", json={"home_score": 20, "away_score": 6})
    response = client.post("/api/games/schedule/confirm", json={"games": [
        {**row, "start_time": "13:00"}, {**row, "away_team_id": other}
    ]})
    assert response.status_code == 409
    games = client.get("/api/games").json()
    assert len(games) == 1
    assert games[0]["away_team"]["id"] == away
    assert games[0]["home_score"] == 20


def test_schedule_rejects_duplicate_slots():
    home = create_test_team(name="Home")
    away = create_test_team(name="Away")
    row = dict(home_team_id=home, away_team_id=away, field_number=1, start_time="12:00")
    response = client.post("/api/games/schedule/confirm", json={"games": [row, row]})
    assert response.status_code == 409
    assert client.get("/api/games").json() == []


def test_schedule_cannot_replace_game_with_linked_statistics():
    home = create_test_team(name="Home")
    away = create_test_team(name="Away")
    other = create_test_team(name="Other")
    row = dict(home_team_id=home, away_team_id=away, field_number=1, start_time="12:00")
    client.post("/api/games/schedule/confirm", json={"games": [row]})
    game_id = client.get("/api/games").json()[0]["id"]
    connection = get_connection()
    player_id = connection.execute(
        "INSERT INTO players (name, curp, age) VALUES ('Test', 'TEST000000HTEST00', 20) RETURNING id"
    ).fetchone()["id"]
    connection.execute(
        "INSERT INTO player_week_stats (week, player_id, team_id, game_id) VALUES (1, %s, %s, %s)",
        (player_id, home, game_id),
    )
    connection.commit()
    connection.close()
    response = client.post("/api/games/schedule/confirm", json={"games": [{**row, "away_team_id": other}]})
    assert response.status_code == 409
    assert client.get("/api/games").json()[0]["away_team"]["id"] == away


@pytest.mark.parametrize("field", [7, 8])
def test_schedule_supports_fields_seven_and_eight_and_null_time_reimports(field):
    home = create_test_team(name="Home")
    away = create_test_team(name="Away")
    row = dict(home_team_id=home, away_team_id=away, field_number=field)
    first = client.post("/api/games/schedule/confirm", json={"games": [row]})
    second = client.post("/api/games/schedule/confirm", json={"games": [row]})
    assert first.status_code == second.status_code == 200
    assert second.json()["skipped"] == 1
    assert len(client.get("/api/games").json()) == 1
