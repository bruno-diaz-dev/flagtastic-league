import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.test_games import create_test_team

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://flagtastic:flagtastic@localhost:5432/flagtastic"
)

from database import get_connection
from main import app
from models import UserCreate
from repositories.users import create_user

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


def test_team_staff_is_created_and_can_be_updated():
    response = client.post("/api/teams", json={
        "name": "Staffed Team", "branch": "mixto", "category": "libre",
        "head_coach": "Ana Head", "coach": "Carlos Coach",
        "manager": "Marina Manager"
    })
    assert response.status_code == 201
    team_id = response.json()["id"]
    assert response.json()["head_coach"] == "Ana Head"

    updated = client.patch(f"/api/teams/{team_id}/staff", json={
        "head_coach": "Ana Nueva", "coach": "", "manager": "Marina Manager"
    })
    assert updated.status_code == 200
    assert updated.json()["head_coach"] == "Ana Nueva"
    assert updated.json()["coach"] is None
    assert client.get(f"/api/teams/{team_id}").json()["manager"] == "Marina Manager"


@pytest.mark.parametrize("status", ["pending", "active", "inactive"])
def test_league_admin_can_update_team_status(status):
    team_id = create_test_team(name=f"Status {status}")
    response = client.patch(
        f"/api/teams/{team_id}/status",
        json={"status": status.upper()}
    )
    assert response.status_code == 200
    assert response.json()["status"] == status
    assert client.get(f"/api/teams/{team_id}").json()["status"] == status


def test_team_status_rejects_unknown_value():
    team_id = create_test_team(name="Invalid Status")
    response = client.patch(
        f"/api/teams/{team_id}/status",
        json={"status": "approved"}
    )
    assert response.status_code == 422


def test_league_admin_can_correct_team_name():
    team_id = create_test_team(name="Misspelled Team")
    response = client.patch(
        f"/api/teams/{team_id}/name",
        json={"name": "  Correct Team  "}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Correct Team"
    assert client.get(f"/api/teams/{team_id}").json()["name"] == "Correct Team"


def test_team_name_correction_rejects_duplicate_in_same_division():
    create_test_team(name="Existing Team")
    team_id = create_test_team(name="Team To Rename")
    response = client.patch(
        f"/api/teams/{team_id}/name",
        json={"name": "Existing Team"}
    )
    assert response.status_code == 409
    assert client.get(f"/api/teams/{team_id}").json()["name"] == "Team To Rename"


def test_admin_can_assign_existing_representative_to_historical_team():
    representative = create_user(UserCreate(
        email=f"historical-{uuid4().hex}@example.com",
        name="Historical Representative",
        password="supersecret",
        role="team_representative"
    ))
    team_id = create_test_team(name="Historical Team")

    endpoint = f"/api/teams/{team_id}/representatives/{representative['id']}"
    assert client.put(endpoint).status_code == 204
    assert client.put(endpoint).status_code == 204

    connection = get_connection()
    assignments = connection.execute(
        """
        SELECT COUNT(*) AS total FROM team_representatives
        WHERE user_id = %s AND team_id = %s
        """,
        (representative["id"], team_id)
    ).fetchone()
    connection.close()
    assert assignments["total"] == 1

    visible_assignments = client.get(
        "/api/teams/representative-assignments"
    )
    assert visible_assignments.status_code == 200
    assert {
        "team_id": team_id,
        "user_id": representative["id"],
        "display_name": "Historical Representative"
    } in visible_assignments.json()

    assert client.delete(endpoint).status_code == 204
    assert client.delete(endpoint).status_code == 404
    remaining = client.get("/api/teams/representative-assignments").json()
    assert not any(
        assignment["team_id"] == team_id
        and assignment["user_id"] == representative["id"]
        for assignment in remaining
    )


def test_admin_can_assign_legacy_representative_without_user_roles_row():
    connection = get_connection()
    representative = connection.execute(
        """
        INSERT INTO users (email, name, password_hash, role)
        VALUES (%s, 'Legacy Representative', 'unused', 'team_representative')
        RETURNING id
        """,
        (f"legacy-{uuid4().hex}@example.com",)
    ).fetchone()
    connection.commit()
    connection.close()
    team_id = create_test_team(name="Legacy Representative Team")

    response = client.put(
        f"/api/teams/{team_id}/representatives/{representative['id']}"
    )
    assert response.status_code == 204

    connection = get_connection()
    assignment = connection.execute(
        """
        SELECT 1 FROM team_representatives
        WHERE user_id = %s AND team_id = %s
        """,
        (representative["id"], team_id)
    ).fetchone()
    connection.close()
    assert assignment is not None


def test_historical_team_assignment_requires_representative_role():
    player = create_user(UserCreate(
        email=f"player-{uuid4().hex}@example.com",
        name="Player Only",
        password="supersecret",
        role="player"
    ))
    team_id = create_test_team(name="Unassigned Historical Team")

    response = client.put(
        f"/api/teams/{team_id}/representatives/{player['id']}"
    )
    assert response.status_code == 404


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


def test_list_teams_orders_by_branch_category_then_name():
    teams = [
        {"name": "Zorros", "branch": "mixto", "category": "libre"},
        {"name": "Tigres", "branch": "varonil", "category": "u10"},
        {"name": "Águilas", "branch": "femenil", "category": "u6"},
        {"name": "Búfalos", "branch": "varonil", "category": "u10"},
        {"name": "Halcones", "branch": "femenil", "category": "u6"}
    ]
    for team in teams:
        assert client.post("/api/teams", json=team).status_code == 201

    response = client.get("/api/teams")

    assert response.status_code == 200
    assert [
        (team["branch"], team["category"], team["name"])
        for team in response.json()
    ] == [
        ("varonil", "u10", "Búfalos"),
        ("varonil", "u10", "Tigres"),
        ("femenil", "u6", "Águilas"),
        ("femenil", "u6", "Halcones"),
        ("mixto", "libre", "Zorros")
    ]

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


def test_team_manager_can_upload_and_read_team_logo():
    team_id = create_test_team(name="Halcones")
    png = b"\x89PNG\r\n\x1a\nlogo-test"

    response = client.put(
        f"/api/teams/{team_id}/logo",
        files={"file": ("logo.png", png, "image/png")}
    )

    assert response.status_code == 204
    teams = client.get("/api/teams").json()
    first_url = teams[0]["logo_url"]
    assert first_url.startswith(f"/api/teams/{team_id}/logo?v=")

    logo = client.get(f"/api/teams/{team_id}/logo")
    assert logo.status_code == 200
    assert logo.headers["content-type"] == "image/png"
    assert logo.content == png

    replacement = b"\x89PNG\r\n\x1a\nreplacement-logo"
    assert client.put(
        f"/api/teams/{team_id}/logo",
        files={"file": ("replacement.png", replacement, "image/png")}
    ).status_code == 204
    second_url = client.get(f"/api/teams/{team_id}").json()["logo_url"]
    assert second_url.startswith(f"/api/teams/{team_id}/logo?v=")
    assert second_url != first_url


def test_team_manager_can_add_photo_after_player_is_on_roster():
    team_id = create_test_team(name="Imported Roster Team")
    player = client.post(
        f"/api/teams/{team_id}/players",
        json={
            "name": "Roster Photo Player",
            "curp": "ROPP000101HASXXX01",
            "age": 22,
            "jersey_number": 19
        }
    ).json()
    png = b"\x89PNG\r\n\x1a\nplayer-photo"

    response = client.put(
        f"/api/teams/{team_id}/players/{player['id']}/photo",
        files={"file": ("player.png", png, "image/png")}
    )

    assert response.status_code == 204
    roster_player = client.get(f"/api/teams/{team_id}").json()["players"][0]
    assert roster_player["profile_photo_url"].startswith("/media/profiles/")
    photo = client.get(roster_player["profile_photo_url"])
    assert photo.status_code == 200
    assert photo.headers["content-type"] == "image/png"
    assert photo.content == png


def test_team_manager_cannot_update_photo_outside_team_roster():
    managed_team_id = create_test_team(name="Managed Photo Team")
    other_team_id = create_test_team(
        name="Other Photo Team", branch="femenil", category="u18"
    )
    player = client.post(
        f"/api/teams/{other_team_id}/players",
        json={
            "name": "Other Team Player",
            "curp": "OTPP000101MASXXX01",
            "age": 21,
            "jersey_number": 8
        }
    ).json()

    response = client.put(
        f"/api/teams/{managed_team_id}/players/{player['id']}/photo",
        files={"file": ("player.png", b"\x89PNG\r\n\x1a\nphoto", "image/png")}
    )

    assert response.status_code == 404


def test_team_logo_rejects_unsupported_content():
    team_id = create_test_team(name="Halcones")
    response = client.put(
        f"/api/teams/{team_id}/logo",
        files={"file": ("logo.svg", b"<svg></svg>", "image/svg+xml")}
    )
    assert response.status_code == 415


def test_missing_team_logo_returns_not_found():
    team_id = create_test_team(name="Halcones")
    assert client.get(f"/api/teams/{team_id}/logo").status_code == 404
"""API tests for team registration, listing, and detail views."""
