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

    connection.execute(
        "DELETE FROM games"
    )

    connection.execute(
        "DELETE FROM team_players"
    )

    connection.execute(
        "DELETE FROM players"
    )

    connection.execute(
        "DELETE FROM teams"
    )

    connection.commit()
    connection.close()
    
def create_test_team(
    name,
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

def test_get_standings_for_branch_and_category():

    tigres_id = create_test_team(
        name="Tigres"
    )

    ravens_id = create_test_team(
        name="Ravens"
    )

    create_game_response = client.post(
        "/api/games",
        json={
            "home_team_id": tigres_id,
            "away_team_id": ravens_id
        }
    )

    game_id = create_game_response.json()["id"]

    client.patch(
        f"/api/games/{game_id}/score",
        json={
            "home_score": 32,
            "away_score": 24
        }
    )

    response = client.get(
        "/api/standings?branch=varonil&category=libre"
    )

    assert response.status_code == 200

    assert response.json() == [
        {
            "team_id": tigres_id,
            "team_name": "Tigres",
            "wins": 1,
            "losses": 0,
            "points_for": 32,
            "points_against": 24,
            "point_difference": 8
        },
        {
            "team_id": ravens_id,
            "team_name": "Ravens",
            "wins": 0,
            "losses": 1,
            "points_for": 24,
            "points_against": 32,
            "point_difference": -8
        }
    ]