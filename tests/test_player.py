import os
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from repositories import players
from models import UserCreate
from repositories.users import create_user
from services.curp import calendar_age_from_curp

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
        "DELETE FROM users"
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


def create_registered_player(name, aka=None):
    """Create an active player account linked to a searchable identity."""
    email = f"{name.lower().replace(' ', '.')}@example.test"
    user = create_user(UserCreate(
        email=email,
        name=name,
        password="supersecret",
        role="player"
    ))
    connection = get_connection()
    player = connection.execute(
        """
        INSERT INTO players (name, curp, age, aka)
        VALUES (%s, %s, 24, %s)
        RETURNING id
        """,
        (name, f"TEST{user['id']:014d}"[-18:], aka)
    ).fetchone()
    connection.execute(
        "UPDATE users SET player_id = %s WHERE id = %s",
        (player["id"], user["id"])
    )
    connection.commit()
    connection.close()
    return player["id"]

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
    assert data["age"] == calendar_age_from_curp(player["curp"])
    assert data["jersey_number"] == 83
    assert "id" in data


def test_manager_searches_and_adds_a_registered_player_by_name_or_aka():
    team_id = create_test_team()
    player_id = create_registered_player("Cameron Test", aka="Cam")
    create_registered_player("Different Person")

    by_name = client.get(
        f"/api/teams/{team_id}/players/candidates",
        params={"q": "Cameron"}
    )
    by_aka = client.get(
        f"/api/teams/{team_id}/players/candidates",
        params={"q": "Cam"}
    )

    assert by_name.status_code == 200
    assert [candidate["id"] for candidate in by_name.json()] == [player_id]
    assert by_aka.json()[0]["aka"] == "Cam"
    assert "email" not in by_aka.json()[0]
    assert "curp" not in by_aka.json()[0]

    added = client.post(
        f"/api/teams/{team_id}/players/registered",
        json={"player_id": player_id, "jersey_number": 12}
    )
    assert added.status_code == 201
    assert added.json() == {
        "team_id": team_id,
        "player_id": player_id,
        "jersey_number": 12
    }

    roster = client.get(f"/api/teams/{team_id}/players").json()
    assert roster[0]["name"] == "Cameron Test"
    assert roster[0]["jersey_number"] == 12

    no_longer_eligible = client.get(
        f"/api/teams/{team_id}/players/candidates",
        params={"q": "Cam"}
    )
    assert no_longer_eligible.json() == []


def test_manager_adds_roster_only_identity_but_not_division_duplicate():
    team_id = create_test_team(name="First Team")
    other_team_id = create_test_team(name="Second Team")
    registered_player_id = create_registered_player("Registered Player")

    first = client.post(
        f"/api/teams/{team_id}/players/registered",
        json={"player_id": registered_player_id, "jersey_number": 4}
    )
    duplicate = client.post(
        f"/api/teams/{other_team_id}/players/registered",
        json={"player_id": registered_player_id, "jersey_number": 8}
    )

    connection = get_connection()
    unregistered = connection.execute(
        """
        INSERT INTO players (name, curp, age)
        VALUES ('Roster Only', 'ROST000101HASXXX01', 26)
        RETURNING id
        """
    ).fetchone()
    connection.commit()
    connection.close()
    by_name = client.get(
        f"/api/teams/{team_id}/players/candidates",
        params={"q": "Roster Only"}
    )
    roster_only = client.post(
        f"/api/teams/{team_id}/players/registered",
        json={"player_id": unregistered["id"], "jersey_number": 9}
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert by_name.status_code == 200
    assert by_name.json()[0]["id"] == unregistered["id"]
    assert by_name.json()[0]["has_account"] is False
    assert roster_only.status_code == 201

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
        == "Ese numero ya esta registrado en este equipo"
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
        "detail": "Este jugador ya esta registrado en esta rama y categoria"
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


def test_import_roster_from_csv():
    team_id = create_test_team()
    content = (
        "nombre,curp,edad,numero\n"
        "Bruno Diaz,DIBB961215HASXXX00,29,83\n"
        "Selina Kyle,KYLS970101MASXXX01,27,12\n"
    ).encode("utf-8")

    response = client.post(
        f"/api/teams/{team_id}/players/import",
        files={"file": ("roster.csv", content, "text/csv")}
    )

    assert response.status_code == 201
    assert response.json()["imported"] == 2

    roster = client.get(f"/api/teams/{team_id}/players").json()
    assert [player["name"] for player in roster] == ["Selina Kyle", "Bruno Diaz"]
    assert [player["jersey_number"] for player in roster] == [12, 83]


def test_import_roster_derives_completed_age_from_curp_without_age_column():
    team_id = create_test_team()
    content = (
        "nombre,curp,numero\n"
        "Bruno Diaz,DIBB961215HASXXX00,83\n"
    ).encode("utf-8")

    response = client.post(
        f"/api/teams/{team_id}/players/import",
        files={"file": ("roster.csv", content, "text/csv")}
    )

    assert response.status_code == 201
    roster = client.get(f"/api/teams/{team_id}/players").json()
    assert roster[0]["age"] == calendar_age_from_curp("DIBB961215HASXXX00")


def test_team_manager_can_edit_and_deactivate_roster_player():
    team_id = create_test_team()
    created = client.post(
        f"/api/teams/{team_id}/players",
        json={
            "name": "Nombre Incorrecto",
            "curp": "DIBB961215HASXXX00",
            "jersey_number": 83
        }
    ).json()

    updated = client.patch(
        f"/api/teams/{team_id}/players/{created['id']}",
        json={
            "name": "Bruno Diaz",
            "curp": "DIBB961215HASXXX00",
            "jersey_number": 10
        }
    )
    assert updated.status_code == 200
    assert updated.json()["age"] == calendar_age_from_curp("DIBB961215HASXXX00")
    assert updated.json()["jersey_number"] == 10

    removal = client.delete(
        f"/api/teams/{team_id}/players/{created['id']}"
    )
    assert removal.status_code == 204
    assert client.get(f"/api/teams/{team_id}/players").json() == []

    connection = get_connection()
    identity = connection.execute(
        "SELECT name FROM players WHERE id = %s", (created["id"],)
    ).fetchone()
    membership = connection.execute(
        "SELECT active FROM team_players WHERE team_id = %s AND player_id = %s",
        (team_id, created["id"])
    ).fetchone()
    connection.close()
    assert identity["name"] == "Bruno Diaz"
    assert membership["active"] is False


def test_inactive_player_frees_jersey_number_for_current_roster():
    team_id = create_test_team()
    first = client.post(
        f"/api/teams/{team_id}/players",
        json={
            "name": "Former Player", "curp": "DIBB961215HASXXX00",
            "jersey_number": 7
        }
    ).json()
    assert client.delete(
        f"/api/teams/{team_id}/players/{first['id']}"
    ).status_code == 204

    replacement = client.post(
        f"/api/teams/{team_id}/players",
        json={
            "name": "Current Player", "curp": "GOPJ010405HASXXA01",
            "jersey_number": 7
        }
    )
    assert replacement.status_code == 201


def test_import_roster_from_xlsx():
    team_id = create_test_team()
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Nombre", "CURP", "Edad", "Numero"])
    sheet.append(["Diana Prince", "PRID950101MASXXX01", 28, 8])
    content = BytesIO()
    workbook.save(content)
    workbook.close()
    content.seek(0)

    response = client.post(
        f"/api/teams/{team_id}/players/import",
        files={
            "file": (
                "roster.xlsx",
                content.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        }
    )

    assert response.status_code == 201
    assert response.json()["imported"] == 1

    roster = client.get(f"/api/teams/{team_id}/players").json()
    assert roster[0]["name"] == "Diana Prince"
    assert roster[0]["jersey_number"] == 8


def test_invalid_roster_import_rolls_back_all_rows():
    team_id = create_test_team()
    content = (
        "nombre,curp,edad,numero\n"
        "Bruce Wayne,WAYB950101HASXXX01,31,1\n"
        "Clark Kent,KENC950101HASXXX02,32,1\n"
    ).encode("utf-8")

    response = client.post(
        f"/api/teams/{team_id}/players/import",
        files={"file": ("roster.csv", content, "text/csv")}
    )

    assert response.status_code == 422
    assert "fila 3" in response.json()["detail"].lower()
    assert client.get(f"/api/teams/{team_id}/players").json() == []


def test_roster_csv_template_uses_canonical_headers():
    team_id = create_test_team()
    response = client.get(
        f"/api/teams/{team_id}/players/import/template.csv"
    )

    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.decode("utf-8-sig").startswith(
        "nombre,curp,numero"
    )


def test_import_roster_accepts_semicolon_csv_from_excel():
    team_id = create_test_team()
    content = (
        "nombre;curp;edad;numero\n"
        "Barry Allen;ALLB950101HASXXX01;30;7\n"
    ).encode("utf-8")

    response = client.post(
        f"/api/teams/{team_id}/players/import",
        files={"file": ("roster.csv", content, "text/csv")}
    )

    assert response.status_code == 201
    assert response.json()["imported"] == 1
"""API tests for player identity, eligibility, and roster membership."""


def test_reimporting_same_roster_is_idempotent():
    team_id = create_test_team()
    content = (
        "nombre,curp,numero\n"
        "Bruno Diaz,DIBB961215HASXXX00,83\n"
        "Selina Kyle,KYLS970101MASXXX01,12\n"
    ).encode("utf-8")

    first = client.post(
        f"/api/teams/{team_id}/players/import",
        files={"file": ("roster.csv", content, "text/csv")}
    )
    second = client.post(
        f"/api/teams/{team_id}/players/import",
        files={"file": ("roster.csv", content, "text/csv")}
    )

    assert first.status_code == 201
    assert first.json()["created"] == 2
    assert first.json()["skipped"] == 0
    assert second.status_code == 201
    assert second.json()["created"] == 0
    assert second.json()["updated"] == 0
    assert second.json()["skipped"] == 2
    assert second.json()["conflicts"] == []
    assert len(client.get(f"/api/teams/{team_id}/players").json()) == 2


def test_roster_reimport_adds_only_missing_players():
    team_id = create_test_team()
    initial = (
        "nombre,curp,numero\n"
        "Bruno Diaz,DIBB961215HASXXX00,83\n"
    ).encode("utf-8")
    expanded = (
        "nombre,curp,numero\n"
        "Bruno Diaz,DIBB961215HASXXX00,83\n"
        "Selina Kyle,KYLS970101MASXXX01,12\n"
    ).encode("utf-8")

    client.post(
        f"/api/teams/{team_id}/players/import",
        files={"file": ("roster.csv", initial, "text/csv")}
    )
    response = client.post(
        f"/api/teams/{team_id}/players/import",
        files={"file": ("roster.csv", expanded, "text/csv")}
    )

    assert response.status_code == 201
    assert response.json()["created"] == 1
    assert response.json()["skipped"] == 1
    assert response.json()["conflicts"] == []
    assert len(client.get(f"/api/teams/{team_id}/players").json()) == 2


def test_repeating_manual_player_registration_is_safe():
    team_id = create_test_team()
    payload = {
        "name": "Bruno Diaz",
        "curp": "DIBB961215HASXXX00",
        "jersey_number": 83,
    }

    first = client.post(f"/api/teams/{team_id}/players", json=payload)
    second = client.post(f"/api/teams/{team_id}/players", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert len(client.get(f"/api/teams/{team_id}/players").json()) == 1
