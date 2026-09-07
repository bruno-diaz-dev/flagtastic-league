import os

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = (
    "postgresql://flagtastic:flagtastic@localhost:5432/flagtastic_test"
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