"""Representatives may only attach and edit identities they can prove."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from database import get_connection
from dependencies.auth import require_player, require_team_manager
from main import app
from models import UserCreate
from repositories.users import create_user
from services import roster_policy


client = TestClient(app)
REPRESENTATIVE = {"id": 9001, "role": "team_representative", "roles": ["team_representative"]}
PROFILE_PNG = b"\x89PNG\r\n\x1a\nidentity-protection"


@pytest.fixture(autouse=True)
def clean_database():
    connection = get_connection()
    for table in ("team_players", "users", "players", "teams"):
        connection.execute(f"DELETE FROM {table}")
    connection.commit()
    connection.close()


def as_representative():
    app.dependency_overrides[require_team_manager] = lambda: REPRESENTATIVE


def create_team(name, category="libre"):
    response = client.post("/api/teams", json={"name": name, "branch": "varonil", "category": category})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def insert_player(name, curp, with_account=False):
    connection = get_connection()
    player_id = connection.execute(
        "INSERT INTO players (name, curp, age) VALUES (%s, %s, 25) RETURNING id",
        (name, curp)
    ).fetchone()["id"]
    connection.commit()
    connection.close()
    if with_account:
        user = create_user(UserCreate(
            email=f"{curp.lower()}@example.test", name=name,
            password="supersecret", role="player"
        ))
        connection = get_connection()
        connection.execute("UPDATE users SET player_id = %s WHERE id = %s", (player_id, user["id"]))
        connection.commit()
        connection.close()
    return player_id


def add_member(team_id, player_id, jersey):
    connection = get_connection()
    connection.execute(
        "INSERT INTO team_players (team_id, player_id, jersey_number) VALUES (%s, %s, %s)",
        (team_id, player_id, jersey)
    )
    connection.commit()
    connection.close()


def stored_name(player_id):
    connection = get_connection()
    name = connection.execute("SELECT name FROM players WHERE id = %s", (player_id,)).fetchone()["name"]
    connection.close()
    return name


def patch_payload(name, curp, jersey):
    return {"name": name, "curp": curp, "identity_type": "curp", "age": 25, "jersey_number": jersey}


def test_representative_needs_the_matching_curp_to_attach_an_existing_player():
    team_id = create_team("Tigres")
    player_id = insert_player("Cameron Test", "CAMT900101HASXXX01", with_account=True)
    as_representative()

    missing = client.post(f"/api/teams/{team_id}/players/registered",
                          json={"player_id": player_id, "jersey_number": 4})
    wrong = client.post(f"/api/teams/{team_id}/players/registered",
                        json={"player_id": player_id, "jersey_number": 4, "curp": "CAMT900101HASXXX02"})
    unknown = client.post(f"/api/teams/{team_id}/players/registered",
                          json={"player_id": player_id + 999, "jersey_number": 4, "curp": "CAMT900101HASXXX01"})
    right = client.post(f"/api/teams/{team_id}/players/registered",
                        json={"player_id": player_id, "jersey_number": 4, "curp": " camt900101hasxxx01 "})

    assert missing.status_code == 422
    assert wrong.status_code == 404
    # A wrong document and an unknown player give the same answer.
    assert unknown.status_code == 404
    assert wrong.json()["detail"] == unknown.json()["detail"]
    assert right.status_code == 201


def test_administrator_can_attach_without_the_document():
    team_id = create_team("Tigres")
    player_id = insert_player("Cameron Test", "CAMT900101HASXXX01")
    added = client.post(f"/api/teams/{team_id}/players/registered",
                        json={"player_id": player_id, "jersey_number": 4})
    assert added.status_code == 201


def test_representative_cannot_rename_a_player_with_an_account_but_can_change_the_jersey():
    team_id = create_team("Tigres")
    player_id = insert_player("Cameron Test", "CAMT900101HASXXX01", with_account=True)
    add_member(team_id, player_id, 4)
    as_representative()

    renamed = client.patch(f"/api/teams/{team_id}/players/{player_id}",
                           json=patch_payload("Someone Else", "CAMT900101HASXXX01", 4))
    new_document = client.patch(f"/api/teams/{team_id}/players/{player_id}",
                                json=patch_payload("Cameron Test", "CAMT900101HASXXX09", 4))
    jersey = client.patch(f"/api/teams/{team_id}/players/{player_id}",
                          json=patch_payload(" Cameron Test ", "CAMT900101HASXXX01", 11))

    assert renamed.status_code == 409
    assert new_document.status_code == 409
    assert jersey.status_code == 200, jersey.text
    assert jersey.json()["jersey_number"] == 11
    assert stored_name(player_id) == "Cameron Test"


def test_representative_cannot_rename_a_player_on_another_active_roster():
    team_id = create_team("Tigres")
    other_team_id = create_team("Lobos U12", category="u12")
    player_id = insert_player("Shared Player", "SHAP900101HASXXX01")
    add_member(team_id, player_id, 4)
    add_member(other_team_id, player_id, 8)
    as_representative()

    renamed = client.patch(f"/api/teams/{team_id}/players/{player_id}",
                           json=patch_payload("Changed Name", "SHAP900101HASXXX01", 4))
    assert renamed.status_code == 409
    assert stored_name(player_id) == "Shared Player"


def test_representative_still_corrects_a_roster_only_identity_and_admin_any():
    team_id = create_team("Tigres")
    roster_only = insert_player("Roster Ony", "ROST900101HASXXX01")
    with_account = insert_player("Account Player", "ACCP900101HASXXX01", with_account=True)
    add_member(team_id, roster_only, 4)
    add_member(team_id, with_account, 5)

    as_representative()
    fixed = client.patch(f"/api/teams/{team_id}/players/{roster_only}",
                         json=patch_payload("Roster Only", "ROST900101HASXXX01", 4))
    assert fixed.status_code == 200, fixed.text
    assert stored_name(roster_only) == "Roster Only"

    app.dependency_overrides.pop(require_team_manager)
    admin_fix = client.patch(f"/api/teams/{team_id}/players/{with_account}",
                             json=patch_payload("Account Player Fixed", "ACCP900101HASXXX01", 5))
    assert admin_fix.status_code == 200, admin_fix.text
    assert stored_name(with_account) == "Account Player Fixed"


def test_representative_cannot_replace_the_photo_of_a_player_with_an_account():
    team_id = create_team("Tigres")
    player_id = insert_player("Cameron Test", "CAMT900101HASXXX01", with_account=True)
    add_member(team_id, player_id, 4)
    as_representative()

    response = client.put(
        f"/api/teams/{team_id}/players/{player_id}/photo",
        files={"file": ("photo.png", PROFILE_PNG, "image/png")}
    )
    assert response.status_code == 409


def test_import_reports_an_account_owned_curp_listed_with_another_name():
    team_id = create_team("Tigres")
    insert_player("José Pérez", "JOPE900101HASXXX01", with_account=True)
    insert_player("Otra Persona", "OTRP900101HASXXX01", with_account=True)
    csv = (
        "nombre,curp,numero\n"
        "jose perez,JOPE900101HASXXX01,10\n"
        "Nombre Distinto,OTRP900101HASXXX01,11\n"
    )
    response = client.post(
        f"/api/teams/{team_id}/players/import",
        files={"file": ("roster.csv", csv.encode(), "text/csv")}
    )

    assert response.status_code == 201, response.text
    body = response.json()
    # Same person written without accents or capitals is linked as before.
    assert [row["name"] for row in body["rows"]] == ["José Pérez"]
    assert [conflict["reason"] for conflict in body["conflicts"]] == ["identity_mismatch"]
    # The account holder's name is not revealed to the importer.
    assert body["conflicts"][0]["name"] == "Nombre Distinto"


def test_single_registration_rejects_an_account_owned_curp_with_another_name():
    team_id = create_team("Tigres")
    insert_player("Otra Persona", "OTRP900101HASXXX01", with_account=True)
    response = client.post(f"/api/teams/{team_id}/players", json={
        "name": "Nombre Distinto", "curp": "OTRP900101HASXXX01", "age": 25, "jersey_number": 3,
    })
    assert response.status_code == 409


def test_player_cannot_join_a_team_after_the_roster_cutoff(monkeypatch):
    class AfterDeadline(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 16, 6, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(roster_policy, "datetime", AfterDeadline)
    app.dependency_overrides[require_player] = lambda: {
        "id": 42, "player_id": 2, "role": "player", "roles": ["player"],
    }
    response = client.post("/api/me/teams/1", json={"jersey_number": 3})
    assert response.status_code == 403
    assert response.json()["detail"] == roster_policy.ROSTER_CLOSED_MESSAGE
