import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://flagtastic:flagtastic@localhost:5432/flagtastic"
)

from database import get_connection
from main import app
from services.divisions import teams_share_game_division

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


def test_u12_teams_can_play_across_registered_branches():
    assert teams_share_game_division(
        {"branch": "femenil", "category": "u12"},
        {"branch": "varonil", "category": "u12"},
    )
    assert teams_share_game_division(
        {"branch": "mixto", "category": "u12"},
        {"branch": "femenil", "category": "u12"},
    )


def test_non_u12_teams_cannot_play_across_branches():
    home_id = create_test_team("Ravens Fem", "femenil", "u14")
    away_id = create_test_team("Ravens Var", "varonil", "u14")

    response = client.post("/api/games", json={
        "home_team_id": home_id,
        "away_team_id": away_id,
        "field_number": 1,
    })

    assert response.status_code == 409
    assert "U12 permite cruces entre ramas" in response.json()["detail"]


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


def test_admin_can_postpone_and_restore_unplayed_game():
    home_id = create_test_team(name="Home")
    away_id = create_test_team(name="Away")
    game_id = client.post("/api/games", json={
        "home_team_id": home_id,
        "away_team_id": away_id,
        "field_number": 1,
    }).json()["id"]

    postponed = client.patch(
        f"/api/games/{game_id}/status", json={"status": "postponed"}
    )
    assert postponed.status_code == 200
    assert postponed.json() == {"id": game_id, "status": "postponed"}
    assert client.get("/api/games").json()[0]["status"] == "postponed"

    blocked_score = client.patch(
        f"/api/games/{game_id}/score",
        json={"home_score": 20, "away_score": 12},
    )
    assert blocked_score.status_code == 409

    restored = client.patch(
        f"/api/games/{game_id}/status", json={"status": "scheduled"}
    )
    assert restored.json() == {"id": game_id, "status": "scheduled"}


def test_scored_game_is_completed_and_cannot_be_postponed():
    home_id = create_test_team(name="Home")
    away_id = create_test_team(name="Away")
    game_id = client.post("/api/games", json={
        "home_team_id": home_id,
        "away_team_id": away_id,
        "field_number": 1,
    }).json()["id"]

    client.patch(
        f"/api/games/{game_id}/score",
        json={"home_score": 14, "away_score": 6},
    )
    assert client.get("/api/games").json()[0]["status"] == "completed"

    response = client.patch(
        f"/api/games/{game_id}/status", json={"status": "postponed"}
    )
    assert response.status_code == 409


def test_admin_can_delete_one_game():
    home_id = create_test_team(name="Home")
    away_id = create_test_team(name="Away")
    game_id = client.post("/api/games", json={
        "home_team_id": home_id,
        "away_team_id": away_id,
        "field_number": 1,
    }).json()["id"]

    assert client.delete(f"/api/games/{game_id}").status_code == 204
    assert client.get("/api/games").json() == []
    assert client.delete(f"/api/games/{game_id}").status_code == 404


def test_admin_can_delete_only_one_complete_week():
    home_id = create_test_team(name="Home")
    away_id = create_test_team(name="Away")
    for week in (2, 2, 3):
        client.post("/api/games", json={
            "home_team_id": home_id,
            "away_team_id": away_id,
            "week": week,
            "field_number": 1,
        })

    response = client.delete("/api/games/week/2")

    assert response.status_code == 200
    assert response.json() == {"deleted": 2, "week": 2}
    remaining = client.get("/api/games").json()
    assert [game["week"] for game in remaining] == [3]


def test_delete_week_requires_existing_positive_week():
    assert client.delete("/api/games/week/0").status_code == 422
    assert client.delete("/api/games/week/99").status_code == 404


def test_admin_can_postpone_and_restore_all_unplayed_games_in_week():
    home_id = create_test_team(name="Home")
    away_id = create_test_team(name="Away")
    for field in (1, 2):
        client.post("/api/games", json={
            "home_team_id": home_id,
            "away_team_id": away_id,
            "week": 4,
            "field_number": field,
        })

    postponed = client.patch(
        "/api/games/week/4/status", json={"status": "postponed"}
    )
    assert postponed.json() == {"updated": 2, "week": 4, "status": "postponed"}
    assert {game["status"] for game in client.get("/api/games").json()} == {"postponed"}

    restored = client.patch(
        "/api/games/week/4/status", json={"status": "scheduled"}
    )
    assert restored.json() == {"updated": 2, "week": 4, "status": "scheduled"}


def test_week_status_change_leaves_completed_games_unchanged():
    home_id = create_test_team(name="Home")
    away_id = create_test_team(name="Away")
    completed_id = client.post("/api/games", json={
        "home_team_id": home_id, "away_team_id": away_id,
        "week": 5, "field_number": 1,
    }).json()["id"]
    client.post("/api/games", json={
        "home_team_id": home_id, "away_team_id": away_id,
        "week": 5, "field_number": 2,
    })
    client.patch(
        f"/api/games/{completed_id}/score",
        json={"home_score": 21, "away_score": 7},
    )

    response = client.patch(
        "/api/games/week/5/status", json={"status": "postponed"}
    )

    assert response.json()["updated"] == 1
    statuses = {game["id"]: game["status"] for game in client.get("/api/games").json()}
    assert statuses[completed_id] == "completed"
    assert set(statuses.values()) == {"completed", "postponed"}


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
