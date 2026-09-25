import os

import pytest
from fastapi.testclient import TestClient

from tests.test_games import create_test_team

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
        """
        DELETE FROM teams
        """
    )

    # Teams cascade roster memberships; unlinked player identities are then safe
    # to clear so this module never inherits a CURP from another test module.
    connection.execute("DELETE FROM players")

    connection.commit()
    connection.close()

def test_register_team():
    team = {
        "name": "Raptors",
        "branch": "varonil",
        "category": "libre"
    }

    response = client.post(
        "/api/teams",
        json=team
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Raptors"
    assert data["branch"] == "varonil"
    assert data["category"] == "libre"
    assert data["status"] == "pending"

    assert "id" in data


def test_list_teams():
    team = {
        "name": "Raptors",
        "branch": "varonil",
        "category": "libre"
    }

    client.post(
        "/api/teams",
        json=team
    )

    response = client.get(
        "/api/teams"
    )

    assert response.status_code == 200

    teams = response.json()

    assert len(teams) == 1
    assert teams[0]["name"] == "Raptors"
    assert teams[0]["branch"] == "varonil"
    assert teams[0]["category"] == "libre"
    assert teams[0]["status"] == "pending"

def test_get_team_detail_with_roster():
    response = client.post(
        "/api/teams",
        json={
            "name": "Tigres",
            "branch": "varonil",
            "category": "libre"
        }
    )

    team_id = response.json()["id"]

    client.post(
        f"/api/teams/{team_id}/players",
        json={
            "name": "Bruno Diaz",
            "curp": "DIBB961215HASXXX00",
            "age": 29,
            "jersey_number": 83
        }
    )

    response = client.get(
        f"/api/teams/{team_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == team_id
    assert data["name"] == "Tigres"
    assert data["branch"] == "varonil"
    assert data["category"] == "libre"
    assert data["status"] == "pending"

    assert len(data["players"]) == 1

    player = data["players"][0]

    assert player["name"] == "Bruno Diaz"
    assert player["aka"] is None
    assert player["profile_photo_url"] is None
    assert player["age"] == 29
    assert player["jersey_number"] == 83
    assert "id" in player
    assert "team_id" not in player

def test_get_team_detail_not_found():
    response = client.get(
        "/api/teams/9999"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Team not found"
    }

def test_team_branch_and_category_normalized():
    response = client.post(
        "/api/teams",
        json={
            "name": "Nomadas",
            "branch": "Varonil",
            "category": "Libre"
        }
    )

    assert response.status_code == 201

    team = response.json()

    assert team["branch"] == "varonil"
    assert team["category"] == "libre"

def test_create_team_with_invalid_branch():
    response = client.post(
        "/api/teams",
        json={
            "name": "Tigres",
            "branch": "varonill",
            "category": "libre"
        }
    )

    assert response.status_code == 422

def test_create_team_with_invalid_category():
    response = client.post(
        "/api/teams",
        json={
            "name": "Tigres",
            "branch": "varonil",
            "category": "u20"
        }
    )

    assert response.status_code == 422

def test_cannot_create_duplicated_team_in_same_branch_and_category():
    first_response = client.post(
        "/api/teams",
        json={
            "name": "Tigres",
            "branch": "varonil",
            "category": "libre"
        }
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/api/teams",
        json={
            "name": "Tigres",
            "branch": "varonil",
            "category": "libre"
        }
    )

    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "Team already registered in this branch and category"
    }

def test_same_team_name_can_exist_in_different_category():
    first_response = client.post(
        "/api/teams",
        json={
            "name": "Tigres",
            "branch": "varonil",
            "category": "libre"
        }
    )

    second_reponse = client.post(
        "/api/teams",
        json={
            "name": "Tigres",
            "branch": "varonil",
            "category": "u18"
        }
    )

    assert first_response.status_code == 201
    assert second_reponse.status_code == 201
"""API tests for team registration, listing, and detail views."""
