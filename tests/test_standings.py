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
            "away_team_id": ravens_id,
            "field_number": 1
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
            "games_played": 1,
            "wins": 1,
            "losses": 0,
            "points_for": 32,
            "points_against": 24,
            "point_difference": 8
        },
        {
            "team_id": ravens_id,
            "team_name": "Ravens",
            "games_played": 1,
            "wins": 0,
            "losses": 1,
            "points_for": 24,
            "points_against": 32,
            "point_difference": -8
        }
    ]


def test_team_with_a_loss_ranks_above_team_that_has_not_played():
    winner_id = create_test_team("Winner")
    loser_id = create_test_team("Loser")
    idle_id = create_test_team("Idle")

    game = client.post("/api/games", json={
        "home_team_id": winner_id,
        "away_team_id": loser_id,
        "field_number": 1,
    }).json()
    assert client.patch(f"/api/games/{game['id']}/score", json={
        "home_score": 14,
        "away_score": 6,
    }).status_code == 200

    standings = client.get(
        "/api/standings?branch=varonil&category=libre"
    )

    assert standings.status_code == 200
    assert [team["team_id"] for team in standings.json()] == [
        winner_id, loser_id, idle_id
    ]


@pytest.mark.parametrize("category", ["u8", "u10", "u12"])
def test_youth_standings_combine_all_registered_branches(category):
    home_id = create_test_team("Rancheros", "varonil", category)
    away_id = create_test_team("Rancheras Flag", "femenil", category)
    idle_id = create_test_team("Nomadas", "mixto", category)

    game = client.post("/api/games", json={
        "home_team_id": home_id,
        "away_team_id": away_id,
        "field_number": 1,
    }).json()
    assert client.patch(f"/api/games/{game['id']}/score", json={
        "home_score": 20,
        "away_score": 12,
    }).status_code == 200

    standings = client.get(
        f"/api/standings?branch=femenil&category={category}"
    )
    assert standings.status_code == 200
    assert [team["team_id"] for team in standings.json()] == [
        home_id, away_id, idle_id
    ]
"""API tests for division standings and ranking rules."""



def test_games_played_is_wins_plus_losses_excluding_unplayed_games():
    home_id = create_test_team("Played Home")
    away_id = create_test_team("Played Away")
    idle_id = create_test_team("Never Played")

    for home_score, away_score in [(14, 6), (6, 12)]:
        game = client.post("/api/games", json={
            "home_team_id": home_id,
            "away_team_id": away_id,
            "field_number": 1,
        }).json()
        assert client.patch(f"/api/games/{game['id']}/score", json={
            "home_score": home_score,
            "away_score": away_score,
        }).status_code == 200

    # Scheduled and postponed games do not increase the played count.
    for status in ("scheduled", "postponed"):
        game = client.post("/api/games", json={
            "home_team_id": home_id,
            "away_team_id": idle_id,
            "field_number": 1,
        }).json()
        if status == "postponed":
            assert client.patch(f"/api/games/{game['id']}/status", json={
                "status": status,
            }).status_code == 200

    response = client.get("/api/standings?branch=varonil&category=libre")
    assert response.status_code == 200
    teams = {team["team_id"]: team for team in response.json()}
    assert teams[home_id]["games_played"] == 2
    assert teams[away_id]["games_played"] == 2
    assert teams[idle_id]["games_played"] == 0
    assert teams[home_id]["games_played"] == (
        teams[home_id]["wins"] + teams[home_id]["losses"]
    )
