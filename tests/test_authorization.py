"""HTTP tests for least-privilege write authorization."""

import os
from uuid import uuid4

from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://flagtastic:flagtastic@localhost:5432/flagtastic"
)

from main import app
from database import get_connection
from models import UserCreate
from repositories.users import create_user


client = TestClient(app, base_url="https://testserver")


def disable_test_authorization_override():
    """Exercise the real dependency instead of the domain-test override."""
    app.dependency_overrides.clear()
    client.cookies.clear()


def unique_identity(prefix):
    identifier = uuid4().hex
    return f"{prefix}-{identifier}", f"{prefix}-{identifier}@example.test"


def login(email, password):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )


def test_anonymous_user_cannot_create_team():
    disable_test_authorization_override()
    team_name, _ = unique_identity("anonymous-team")

    response = client.post(
        "/api/teams",
        json={"name": team_name, "branch": "varonil", "category": "libre"}
    )

    assert response.status_code == 401


def test_anonymous_user_cannot_manage_game_state_or_delete_games():
    disable_test_authorization_override()

    responses = (
        client.patch("/api/games/999999/status", json={"status": "postponed"}),
        client.patch("/api/games/week/1/status", json={"status": "postponed"}),
        client.delete("/api/games/999999"),
        client.delete("/api/games/week/1"),
    )

    assert all(response.status_code == 401 for response in responses)


def test_player_cannot_create_team():
    disable_test_authorization_override()
    team_name, email = unique_identity("player")
    create_user(UserCreate(
        email=email,
        name="Player",
        password="supersecret",
        role="player"
    ))
    login(email, "supersecret")

    response = client.post(
        "/api/teams",
        json={"name": team_name, "branch": "varonil", "category": "libre"}
    )

    assert response.status_code == 403


def test_representative_creates_and_is_assigned_to_team():
    disable_test_authorization_override()
    team_name, email = unique_identity("representative-team")
    representative = create_user(UserCreate(
        email=email,
        name="Representative",
        password="supersecret",
        role="team_representative"
    ))
    assert login(email, "supersecret").status_code == 200

    response = client.post(
        "/api/teams",
        json={"name": team_name, "branch": "femenil", "category": "u18"}
    )
    assert response.status_code == 201

    connection = get_connection()
    assignment = connection.execute(
        """
        SELECT 1 FROM team_representatives
        WHERE user_id = %s AND team_id = %s
        """,
        (representative["id"], response.json()["id"])
    ).fetchone()
    connection.close()
    assert assignment is not None


def test_league_admin_can_create_team():
    disable_test_authorization_override()
    team_name, email = unique_identity("admin")
    admin = create_user(UserCreate(
        email=email,
        name="Admin",
        password="supersecret",
        role="league_admin"
    ))
    login(email, "supersecret")

    response = client.post(
        "/api/teams",
        json={"name": team_name, "branch": "varonil", "category": "libre"}
    )

    assert response.status_code == 201
    connection = get_connection()
    assignment = connection.execute(
        "SELECT 1 FROM team_representatives WHERE user_id = %s AND team_id = %s",
        (admin["id"], response.json()["id"])
    ).fetchone()
    connection.close()
    assert assignment is not None


def test_team_representative_can_manage_only_assigned_team():
    disable_test_authorization_override()
    assigned_name, email = unique_identity("representative")
    other_name, _ = unique_identity("other-team")
    representative = create_user(UserCreate(
        email=email,
        name="Representative",
        password="supersecret",
        role="team_representative"
    ))

    connection = get_connection()
    assigned_team = connection.execute(
        """
        INSERT INTO teams (name, branch, category)
        VALUES (%s, 'varonil', 'libre')
        RETURNING id
        """,
        (assigned_name,)
    ).fetchone()
    other_team = connection.execute(
        """
        INSERT INTO teams (name, branch, category)
        VALUES (%s, 'mixto', 'libre')
        RETURNING id
        """,
        (other_name,)
    ).fetchone()
    connection.execute(
        """
        INSERT INTO team_representatives (user_id, team_id)
        VALUES (%s, %s)
        """,
        (representative["id"], assigned_team["id"])
    )
    connection.commit()
    connection.close()

    login(email, "supersecret")
    assigned_detail = client.get(f"/api/teams/{assigned_team['id']}")
    other_detail = client.get(f"/api/teams/{other_team['id']}")
    assert assigned_detail.json()["can_manage"] is True
    assert other_detail.json()["can_manage"] is False

    player = {
        "name": "Roster Player",
        "curp": uuid4().hex[:18].upper(),
        "age": 24,
        "jersey_number": 7
    }

    assigned_response = client.post(
        f"/api/teams/{assigned_team['id']}/players",
        json=player
    )
    other_response = client.post(
        f"/api/teams/{other_team['id']}/players",
        json={**player, "curp": uuid4().hex[:18].upper()}
    )

    assert assigned_response.status_code == 201
    assert other_response.status_code == 403

    png = b"\x89PNG\r\n\x1a\nrepresentative-logo"
    assigned_logo = client.put(
        f"/api/teams/{assigned_team['id']}/logo",
        files={"file": ("logo.png", png, "image/png")}
    )
    other_logo = client.put(
        f"/api/teams/{other_team['id']}/logo",
        files={"file": ("logo.png", png, "image/png")}
    )
    assert assigned_logo.status_code == 204
    assert other_logo.status_code == 403

    assigned_staff = client.patch(
        f"/api/teams/{assigned_team['id']}/staff",
        json={"head_coach": "Head Coach", "coach": "Coach", "manager": "Manager"}
    )
    other_staff = client.patch(
        f"/api/teams/{other_team['id']}/staff",
        json={"head_coach": "No Access", "coach": "", "manager": ""}
    )
    assert assigned_staff.status_code == 200
    assert other_staff.status_code == 403

    roster_csv = b"nombre,curp,edad,numero\nImported Player,ABCD000101HASXXX01,25,12\n"
    other_import = client.post(
        f"/api/teams/{other_team['id']}/players/import",
        files={"file": ("roster.csv", roster_csv, "text/csv")}
    )
    other_template = client.get(
        f"/api/teams/{other_team['id']}/players/import/template.csv"
    )
    assert other_import.status_code == 403
    assert other_template.status_code == 403
    other_candidate_search = client.get(
        f"/api/teams/{other_team['id']}/players/candidates",
        params={"q": "Player"}
    )
    other_registered_add = client.post(
        f"/api/teams/{other_team['id']}/players/registered",
        json={"player_id": 999999, "jersey_number": 18}
    )
    assert other_candidate_search.status_code == 403
    assert other_registered_add.status_code == 403

    player_id = assigned_response.json()["id"]
    assigned_photo = client.put(
        f"/api/teams/{assigned_team['id']}/players/{player_id}/photo",
        files={"file": ("player.png", png, "image/png")}
    )
    other_photo = client.put(
        f"/api/teams/{other_team['id']}/players/{player_id}/photo",
        files={"file": ("player.png", png, "image/png")}
    )
    assert assigned_photo.status_code == 204
    assert other_photo.status_code == 403

    cross_team_edit = client.patch(
        f"/api/teams/{other_team['id']}/players/{player_id}",
        json={
            "name": "Unauthorized Edit",
            "curp": "DIBB961215HASXXX00",
            "jersey_number": 9
        }
    )
    cross_team_removal = client.delete(
        f"/api/teams/{other_team['id']}/players/{player_id}"
    )
    assert cross_team_edit.status_code == 403
    assert cross_team_removal.status_code == 403


def test_league_admin_can_grant_another_admin_role():
    disable_test_authorization_override()
    _, admin_email = unique_identity("role-admin")
    admin = create_user(UserCreate(
        email=admin_email, name="League Admin", password="supersecret",
        role="league_admin"
    ))
    _, user_email = unique_identity("future-admin")
    user = create_user(UserCreate(
        email=user_email, name="Future Admin", password="supersecret",
        role="team_representative"
    ))
    assert login(admin_email, "supersecret").status_code == 200

    response = client.patch(
        f"/api/admin/users/{user['id']}/role",
        json={"role": "league_admin"}
    )
    assert response.status_code == 200
    assert response.json()["role"] == "league_admin"
    assert "password" not in response.text


def test_league_admin_can_create_admin_referee_without_player_identity():
    disable_test_authorization_override()
    _, admin_email = unique_identity("staff-creator")
    create_user(UserCreate(
        email=admin_email, name="League Admin", password="supersecret",
        role="league_admin"
    ))
    _, staff_email = unique_identity("president")
    assert login(admin_email, "supersecret").status_code == 200

    response = client.post(
        "/api/admin/users",
        json={
            "email": staff_email,
            "name": "League President",
            "password": "anothersecret",
            "roles": ["league_admin", "referee"]
        }
    )

    assert response.status_code == 201
    assert response.json()["roles"] == ["league_admin", "referee"]
    assert "player_id" not in response.json()
    assert "password_hash" not in response.text
    assert '"password":' not in response.text

    client.cookies.clear()
    assert login(staff_email, "anothersecret").status_code == 200
    assert client.get("/api/admin/users").status_code == 403


def test_league_admin_can_update_referee_aka():
    disable_test_authorization_override()
    _, admin_email = unique_identity("aka-admin")
    create_user(UserCreate(
        email=admin_email, name="League Admin", password="supersecret",
        role="league_admin"
    ))
    _, referee_email = unique_identity("aka-official")
    referee = create_user(UserCreate(
        email=referee_email, name="Official Legal Name",
        password="supersecret", role="referee"
    ))
    assert login(admin_email, "supersecret").status_code == 200

    response = client.patch(
        f"/api/admin/users/{referee['id']}/referee-aka",
        json={"aka": "Jimmy"}
    )

    assert response.status_code == 200
    assert response.json()["aka"] == "Jimmy"
    assert response.json()["display_name"] == "Jimmy"
    roster = client.get("/api/referees").json()
    listed = next(item for item in roster if item["id"] == referee["id"])
    assert listed["display_name"] == "Jimmy"


def test_non_admin_cannot_update_referee_aka():
    disable_test_authorization_override()
    _, referee_email = unique_identity("aka-denied")
    referee = create_user(UserCreate(
        email=referee_email, name="Referee", password="supersecret",
        role="referee"
    ))
    assert login(referee_email, "supersecret").status_code == 200

    response = client.patch(
        f"/api/admin/users/{referee['id']}/referee-aka",
        json={"aka": "Unauthorized"}
    )

    assert response.status_code == 403


def test_admin_cannot_assign_referee_aka_without_referee_role():
    disable_test_authorization_override()
    _, admin_email = unique_identity("aka-role-admin")
    create_user(UserCreate(
        email=admin_email, name="League Admin", password="supersecret",
        role="league_admin"
    ))
    _, representative_email = unique_identity("aka-representative")
    representative = create_user(UserCreate(
        email=representative_email, name="Representative",
        password="supersecret", role="team_representative"
    ))
    assert login(admin_email, "supersecret").status_code == 200

    response = client.patch(
        f"/api/admin/users/{representative['id']}/referee-aka",
        json={"aka": "Not an official"}
    )

    assert response.status_code == 409


def test_non_admin_cannot_create_staff_account():
    disable_test_authorization_override()
    _, referee_email = unique_identity("staff-denied")
    create_user(UserCreate(
        email=referee_email, name="Referee", password="supersecret",
        role="referee"
    ))
    _, staff_email = unique_identity("forbidden-staff")
    assert login(referee_email, "supersecret").status_code == 200

    response = client.post(
        "/api/admin/users",
        json={
            "email": staff_email,
            "name": "Unauthorized Staff",
            "password": "anothersecret",
            "roles": ["league_admin"]
        }
    )

    assert response.status_code == 403


def test_league_admin_cannot_remove_own_admin_role():
    disable_test_authorization_override()
    _, email = unique_identity("self-admin")
    admin = create_user(UserCreate(
        email=email, name="League Admin", password="supersecret",
        role="league_admin"
    ))
    login(email, "supersecret")

    response = client.patch(
        f"/api/admin/users/{admin['id']}/role",
        json={"role": "team_representative"}
    )
    assert response.status_code == 409


def test_non_admin_cannot_list_users():
    disable_test_authorization_override()
    _, email = unique_identity("non-admin")
    create_user(UserCreate(
        email=email, name="Representative", password="supersecret",
        role="team_representative"
    ))
    login(email, "supersecret")

    assert client.get("/api/admin/users").status_code == 403


def test_league_admin_can_delete_another_account_but_not_their_own():
    disable_test_authorization_override()
    _, admin_email = unique_identity("delete-user-admin")
    admin = create_user(UserCreate(
        email=admin_email, name="Admin", password="supersecret",
        role="league_admin"
    ))
    _, user_email = unique_identity("delete-user-target")
    target = create_user(UserCreate(
        email=user_email, name="Target", password="supersecret",
        role="team_representative"
    ))
    assert login(admin_email, "supersecret").status_code == 200

    assert client.delete(f"/api/admin/users/{admin['id']}").status_code == 409
    assert client.delete(f"/api/admin/users/{target['id']}").status_code == 204
    assert client.delete(f"/api/admin/users/{target['id']}").status_code == 404

    client.cookies.clear()
    assert login(user_email, "supersecret").status_code == 401


def test_only_league_admin_can_delete_team():
    disable_test_authorization_override()
    team_name, player_email = unique_identity("delete-team")
    player = create_user(UserCreate(
        email=player_email, name="Player", password="supersecret",
        role="player"
    ))
    connection = get_connection()
    team = connection.execute(
        """
        INSERT INTO teams (name, branch, category)
        VALUES (%s, 'mixto', 'libre')
        RETURNING id
        """,
        (team_name,)
    ).fetchone()
    connection.commit()
    connection.close()

    assert login(player["email"], "supersecret").status_code == 200
    assert client.delete(f"/api/teams/{team['id']}").status_code == 403

    client.cookies.clear()
    _, admin_email = unique_identity("delete-admin")
    create_user(UserCreate(
        email=admin_email, name="Admin", password="supersecret",
        role="league_admin"
    ))
    assert login(admin_email, "supersecret").status_code == 200
    assert client.delete(f"/api/teams/{team['id']}").status_code == 204
    assert client.get(f"/api/teams/{team['id']}").status_code == 404


def test_only_league_admin_can_change_team_status():
    disable_test_authorization_override()
    team_name, representative_email = unique_identity("status-team")
    representative = create_user(UserCreate(
        email=representative_email, name="Representative",
        password="supersecret", role="team_representative"
    ))
    connection = get_connection()
    team = connection.execute(
        """
        INSERT INTO teams (name, branch, category)
        VALUES (%s, 'varonil', 'u18') RETURNING id
        """,
        (team_name,)
    ).fetchone()
    connection.execute(
        "INSERT INTO team_representatives (user_id, team_id) VALUES (%s, %s)",
        (representative["id"], team["id"])
    )
    connection.commit()
    connection.close()

    assert login(representative_email, "supersecret").status_code == 200
    assert client.patch(
        f"/api/teams/{team['id']}/status", json={"status": "active"}
    ).status_code == 403

    client.cookies.clear()
    _, admin_email = unique_identity("status-admin")
    create_user(UserCreate(
        email=admin_email, name="Admin", password="supersecret",
        role="league_admin"
    ))
    assert login(admin_email, "supersecret").status_code == 200
    approved = client.patch(
        f"/api/teams/{team['id']}/status", json={"status": "active"}
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "active"


def test_only_league_admin_can_assign_historical_team_representative():
    disable_test_authorization_override()
    team_name, representative_email = unique_identity("historical-owner")
    representative = create_user(UserCreate(
        email=representative_email, name="Representative",
        password="supersecret", role="team_representative"
    ))
    connection = get_connection()
    team = connection.execute(
        """
        INSERT INTO teams (name, branch, category)
        VALUES (%s, 'femenil', 'libre') RETURNING id
        """,
        (team_name,)
    ).fetchone()
    connection.commit()
    connection.close()

    assert login(representative_email, "supersecret").status_code == 200
    endpoint = f"/api/teams/{team['id']}/representatives/{representative['id']}"
    assert client.put(endpoint).status_code == 403
    assert client.delete(endpoint).status_code == 403
    assert client.get("/api/teams/representative-assignments").status_code == 403

    client.cookies.clear()
    _, admin_email = unique_identity("historical-owner-admin")
    create_user(UserCreate(
        email=admin_email, name="Admin", password="supersecret",
        role="league_admin"
    ))
    assert login(admin_email, "supersecret").status_code == 200
    assert client.put(endpoint).status_code == 204
    assignments = client.get("/api/teams/representative-assignments")
    assert assignments.status_code == 200
    assert any(
        item["team_id"] == team["id"]
        and item["user_id"] == representative["id"]
        for item in assignments.json()
    )
    assert client.delete(endpoint).status_code == 204


def test_only_league_admin_can_correct_team_name():
    disable_test_authorization_override()
    team_name, representative_email = unique_identity("rename-team")
    representative = create_user(UserCreate(
        email=representative_email, name="Representative",
        password="supersecret", role="team_representative"
    ))
    connection = get_connection()
    team = connection.execute(
        """
        INSERT INTO teams (name, branch, category)
        VALUES (%s, 'mixto', 'libre') RETURNING id
        """,
        (team_name,)
    ).fetchone()
    connection.execute(
        "INSERT INTO team_representatives (user_id, team_id) VALUES (%s, %s)",
        (representative["id"], team["id"])
    )
    connection.commit()
    connection.close()

    assert login(representative_email, "supersecret").status_code == 200
    endpoint = f"/api/teams/{team['id']}/name"
    assert client.patch(endpoint, json={"name": "Representative Edit"}).status_code == 403

    client.cookies.clear()
    _, admin_email = unique_identity("rename-admin")
    create_user(UserCreate(
        email=admin_email, name="Admin", password="supersecret",
        role="league_admin"
    ))
    assert login(admin_email, "supersecret").status_code == 200
    corrected_name, _ = unique_identity("admin-correction")
    response = client.patch(endpoint, json={"name": corrected_name})
    assert response.status_code == 200
    assert response.json()["name"] == corrected_name



def test_league_admin_can_reset_another_users_password_and_force_change():
    disable_test_authorization_override()
    _, admin_email = unique_identity("password-reset-admin")
    create_user(UserCreate(
        email=admin_email,
        name="Reset Admin",
        password="adminsecret",
        role="league_admin"
    ))
    _, target_email = unique_identity("password-reset-target")
    target = create_user(UserCreate(
        email=target_email,
        name="Reset Target",
        password="oldsecret",
        role="league_admin"
    ))

    target_client = TestClient(app, base_url="https://testserver")
    assert target_client.post(
        "/api/auth/login",
        json={"email": target_email, "password": "oldsecret"}
    ).status_code == 200

    assert login(admin_email, "adminsecret").status_code == 200
    response = client.post(
        f"/api/admin/users/{target['id']}/reset-password"
    )

    assert response.status_code == 200
    body = response.json()
    temporary_password = body["temporary_password"]
    assert len(temporary_password) >= 8
    assert body["must_change_password"] is True

    # All existing sessions are revoked immediately.
    assert target_client.get("/api/auth/me").status_code == 401

    target_client.cookies.clear()
    assert target_client.post(
        "/api/auth/login",
        json={"email": target_email, "password": "oldsecret"}
    ).status_code == 401

    temporary_login = target_client.post(
        "/api/auth/login",
        json={"email": target_email, "password": temporary_password}
    )
    assert temporary_login.status_code == 200
    assert temporary_login.json()["must_change_password"] is True

    # The temporary credential cannot be used for normal app access.
    blocked = target_client.get("/api/admin/users")
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == (
        "Debes cambiar tu contraseña antes de continuar"
    )

    changed = target_client.post(
        "/api/auth/change-password",
        json={
            "current_password": temporary_password,
            "new_password": "replacementsecret",
        }
    )
    assert changed.status_code == 204

    target_client.cookies.clear()
    final_login = target_client.post(
        "/api/auth/login",
        json={"email": target_email, "password": "replacementsecret"}
    )
    assert final_login.status_code == 200
    assert "must_change_password" not in final_login.json()


def test_non_admin_cannot_reset_another_users_password():
    disable_test_authorization_override()
    _, representative_email = unique_identity("password-reset-representative")
    create_user(UserCreate(
        email=representative_email,
        name="Representative",
        password="supersecret",
        role="team_representative"
    ))
    _, target_email = unique_identity("password-reset-target")
    target = create_user(UserCreate(
        email=target_email,
        name="Target",
        password="oldsecret",
        role="referee"
    ))

    assert login(representative_email, "supersecret").status_code == 200
    response = client.post(
        f"/api/admin/users/{target['id']}/reset-password"
    )

    assert response.status_code == 403


def test_admin_cannot_reset_own_password_from_user_admin():
    disable_test_authorization_override()
    _, admin_email = unique_identity("self-reset-admin")
    admin = create_user(UserCreate(
        email=admin_email,
        name="Self Reset Admin",
        password="supersecret",
        role="league_admin"
    ))

    assert login(admin_email, "supersecret").status_code == 200
    response = client.post(
        f"/api/admin/users/{admin['id']}/reset-password"
    )

    assert response.status_code == 409


def test_account_recovery_replaces_email_revokes_access_and_preserves_identity():
    from repositories.password_resets import create_password_reset, consume_password_reset
    from repositories.users import get_user_by_id, get_user_by_email
    from repositories.sessions import create_session
    disable_test_authorization_override()
    _, admin_email = unique_identity("recovery-admin")
    create_user(UserCreate(email=admin_email, name="Admin", password="adminsecret", role="league_admin"))
    _, old_email = unique_identity("compromised")
    target = create_user(UserCreate(email=old_email, name="Target", password="oldsecret", role="referee"))
    session = create_session(target["id"])
    reset = create_password_reset(old_email)
    before = get_user_by_id(target["id"])
    _, new_email = unique_identity("replacement")
    assert login(admin_email, "adminsecret").status_code == 200
    response = client.post(f"/api/admin/users/{target['id']}/recover-account", json={"email": f" {new_email.upper()} ", "identity_confirmed": True})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == new_email
    after = get_user_by_id(target["id"])
    for key in ("id", "name", "roles", "player_id"):
        assert after.get(key) == before.get(key)
    assert get_user_by_email(old_email) is None
    assert consume_password_reset(reset["token"], "attackerpassword") is False
    assert TestClient(app).get("/api/auth/me", headers={"Authorization": f"Bearer {session['token']}"}).status_code == 401
    assert login(new_email, "oldsecret").status_code == 401
    assert login(new_email, body["temporary_password"]).json()["must_change_password"] is True


def test_account_recovery_conflict_rolls_back_and_requires_confirmation():
    from repositories.users import get_user_by_id
    disable_test_authorization_override()
    _, admin_email = unique_identity("recovery-conflict-admin")
    admin = create_user(UserCreate(email=admin_email, name="Admin", password="adminsecret", role="league_admin"))
    _, old_email = unique_identity("recovery-conflict-target")
    target = create_user(UserCreate(email=old_email, name="Target", password="oldsecret", role="referee"))
    assert login(admin_email, "adminsecret").status_code == 200
    endpoint = f"/api/admin/users/{target['id']}/recover-account"
    for payload in ({"email": "new@example.test"}, {"email": "new@example.test", "identity_confirmed": False}, {"email": "invalid", "identity_confirmed": True}):
        assert client.post(endpoint, json=payload).status_code == 422
    assert client.post(endpoint, json={"email": admin_email, "identity_confirmed": True}).status_code == 409
    assert get_user_by_id(target["id"])["email"] == old_email
    assert client.post(f"/api/admin/users/{admin['id']}/recover-account", json={"email": "new@example.test", "identity_confirmed": True}).status_code == 409
    assert client.post('/api/admin/users/2147483647/recover-account', json={"email": "new@example.test", "identity_confirmed": True}).status_code == 404
    assert login(old_email, "oldsecret").status_code == 200
    assert client.post(endpoint, json={"email": "new@example.test", "identity_confirmed": True}).status_code == 403
    client.cookies.clear()
    assert client.post(endpoint, json={"email": "new@example.test", "identity_confirmed": True}).status_code == 401
