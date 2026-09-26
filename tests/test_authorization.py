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
