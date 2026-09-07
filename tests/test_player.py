import os

import pytest
from fastapi.testclient import TestClient
from database import get_connection
from repositories import players

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
        "DELETE FROM players"
    )

    connection.execute(
        "DELETE FROM teams"
    )

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

def test_register_player():
    team_id = create_test_team()

    player = {
        "name": "Bruno Diaz",
        "curp": "DIBB961215HASXXX01",
        "age": 29,
        "jersey_number": 83
    }

    response = client.post(
        f"/api/teams/{team_id}/players",
        json=player
    )

    assert response.status_code == 201

    data = response.json()

    assert data["team_id"] == team_id
    assert data["name"] == "Bruno Diaz"
    assert data["age"] == 29
    assert data["jersey_number"] == 83
    assert "id" in data

def test_get_team_roster():
    team_id = create_test_team()

    client.post(
        f"/api/teams/{team_id}/players",
        json={
            "name": "Bruno Diaz",
            "curp": "DIBB961215HASXXX01",
            "age": 29,
            "jersey_number": 83
        }
    )

    response = client.get(
        f"/api/teams/{team_id}/players"
    )

    assert response.status_code == 200

    players = response.json()

    assert len(players) == 1
    assert players[0]["name"] == "Bruno Diaz"
    assert players[0]["jersey_number"] == 83

    # the public roster should never expose the player's curp

    assert "curp" not in players[0]

def test_register_player_in_nonexistent_team():
    player = {
        "name": "Bruno Diaz",
        "curp": "DIBB961218HASXXX01",
        "age": 29,
        "jersey_number": 83
    }

    response = client.post(
        "/api/teams/9999/players",
        json=player
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Team not found"

def test_duplicated_jersey_number():
    team_id = create_test_team()

    first_player = {
        "name": "Carlos Lopez",
        "curp": "LOPC950101HASXX002",
        "age": 31,
        "jersey_number": 83
    }

    second_player = {
        "name": "Jose Gomez",
        "curp": "GOPJ010405HASXX001",
        "age": 21,
        "jersey_number": 83
    }

    first_response = client.post(
        f"/api/teams/{team_id}/players",
        json=first_player
    )

    second_response = client.post(
        f"/api/teams/{team_id}/players",
        json=second_player
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    assert (
        second_response.json()["detail"]
        == "Jersey number already registered in this team"
    )

def test_player_can_join_different_branches():
    tigres_id = create_test_team(
        name="Tigres",
        branch="varonil",
        category="libre"
    )

    ravens_id = create_test_team(
        name="Ravens",
        branch="mixto",
        category="libre"
    )

    player = {
        "name": "Carlos Lopez",
        "curp": "LOPC950101HASXX002",
        "age": 31,
        "jersey_number": 83
    }

    first_response = client.post(
        f"/api/teams/{tigres_id}/players",
        json=player
    )

    second_response = client.post(
        f"/api/teams/{ravens_id}/players",
        json=player
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

def test_player_can_join_different_categories():
    u18_team_id = create_test_team(
        name="Nomadas U18",
        branch="varonil",
        category="u18"
    )

    u16_team_id = create_test_team(
        name="Nomadas U16",
        branch="varonil",
        category="u16"
    )

    player = {
        "name": "Carlos Lopez",
        "curp":"LOPC110101HASXX002",
        "age": 15,
        "jersey_number": 52
    }

    first_response = client.post(
        f"/api/teams/{u18_team_id}/players",
        json=player
    )

    second_response = client.post(

        f"/api/teams/{u16_team_id}/players",
        json=player
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

def test_player_duplicated_in_branch_and_category():
    tigres_id = create_test_team(
        name="Tigres",
        branch="varonil",
        category="libre"
    )

    hawks_id = create_test_team(
        name="hawks",
        branch="varonil",
        category="libre"
    )

    player = {
        "name": "Carlos Lopez",
        "curp": "LOPC950101HASXX002",
        "age": 31,
        "jersey_number": 83
    }

    first_response = client.post(
        f"/api/teams/{tigres_id}/players",
        json=player
    )

    second_response = client.post(
        f"/api/teams/{hawks_id}/players",
        json=player
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    assert second_response.json() == {
        "detail": "Player already registered in this branch and category"
    }

def test_same_jersey_number_in_different_teams():
    tigres_id = create_test_team(
        name="Tigres",
        branch="varonil",
        category="libre"
    )

    hawks_id = create_test_team(
        name="Hawks",
        branch="mixto",
        category="libre"
    )

    first_player = {
        "name": "Bruno Diaz",
        "curp": "DIBB961215HASXXX00",
        "age": 29,
        "jersey_number": 83
    }

    second_player = {
        "name": "Jose Lopez",
        "curp": "LOPJ950101HASXX001",
        "age": 31,
        "jersey_number": 83
    }

    first_response = client.post(
        f"/api/teams/{tigres_id}/players",
        json=first_player
    )

    second_response = client.post(
        f"/api/teams/{hawks_id}/players",
        json=second_player
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

def test_player_duplicity_in_same_team():
    tigres_id = create_test_team(
        name="Tigres",
        branch="varonil",
        category="libre"
    )

    player = {
        "name": "Bruno Diaz",
        "curp": "DIBB961215HASXXX00",
        "age": 29,
        "jersey_number": 83
    }

    first_response = client.post(
        f"/api/teams/{tigres_id}/players",
        json=player
    )

    second_response = client.post(
        f"/api/teams/{tigres_id}/players",
        json=player
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_reused_curp_creates_one_player_with_multiple_memberships():
    tigres_id = create_test_team(
        name="Tigres",
        branch="varonil",
        category="libre"
    )

    ravens_id = create_test_team(
        name="Ravens",
        branch="mixto",
        category="libre"
    )

    player = {
        "name": "Bruno Diaz",
        "curp": "DIBB961215HASXXX00",
        "age": 29,
        "jersey_number": 83
    }

    first_response = client.post(
        f"/api/teams/{tigres_id}/players",
        json=player
    )

    second_response = client.post(
        f"/api/teams/{ravens_id}/players",
        json=player
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    connection = get_connection()

    player_count = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM players
        WHERE curp = %s
        """,
        (player["curp"],)
    ).fetchone()["count"]

    membership_count = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM team_players
        WHERE player_id = (
            SELECT id
            FROM players
            WHERE curp = %s
        )
        """,
        (player["curp"],)
    ).fetchone()["count"]

    connection.close()

    assert player_count == 1
    assert membership_count == 2
