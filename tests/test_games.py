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
            "away_team_id": ravens_id
        }
    )

    assert response.status_code == 201
    
    data = response.json()

    assert "id" in data
    assert data["home_team_id"] == tigres_id
    assert data["away_team_id"] == ravens_id

def test_team_cannot_play_against_itself():
    tigres_id = create_test_team(
        name="Tigres"
    )

    response = client.post(
        "/api/games",
        json={
            "home_team_id": tigres_id,
            "away_team_id": tigres_id
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
            "away_team_id": 9999
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
            "away_team_id": ravens_id 
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

    client.post(
        "/api/games",
        json={
            "home_team_id": tigres_id,
            "away_team_id": ravens_id
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
        "name": "Tigres"
    }

    assert games[0]["away_team"] == {
        "id": ravens_id,
        "name": "Ravens"
    }

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
            "away_team_id": ravens_id
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