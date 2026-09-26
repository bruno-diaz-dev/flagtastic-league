"""Representative dashboard ownership and aggregation tests."""

from fastapi.testclient import TestClient

from database import get_connection
from dependencies.auth import require_team_representative
from main import app
from repositories.representative_dashboard import get_representative_dashboard

client = TestClient(app)


def test_representative_dashboard_contains_only_assigned_teams():
    connection = get_connection()
    representative = connection.execute(
        """
        INSERT INTO users (email, name, password_hash, role)
        VALUES ('dashboard-rep@example.test', 'Dashboard Rep', 'unused', 'team_representative')
        RETURNING id
        """
    ).fetchone()
    assigned = connection.execute(
        """
        INSERT INTO teams (name, branch, category, head_coach)
        VALUES ('Assigned Dashboard Team', 'femenil', 'u18', 'Head Coach')
        RETURNING id
        """
    ).fetchone()
    connection.execute(
        "INSERT INTO teams (name, branch, category) VALUES ('Hidden Dashboard Team', 'femenil', 'u18')"
    )
    connection.execute(
        "INSERT INTO team_representatives (user_id, team_id) VALUES (%s, %s)",
        (representative["id"], assigned["id"])
    )
    connection.commit()
    connection.close()

    user = {"id": representative["id"], "role": "team_representative",
            "roles": ["team_representative"]}
    app.dependency_overrides[require_team_representative] = lambda: user
    response = client.get("/api/me/representative-dashboard")
    app.dependency_overrides.pop(require_team_representative, None)

    assert response.status_code == 200
    assert [team["name"] for team in response.json()["teams"]] == [
        "Assigned Dashboard Team"
    ]
    team = response.json()["teams"][0]
    assert team["head_coach"] == "Head Coach"
    assert team["standing"]["wins"] == 0
    assert team["statistics"]["points"] == 0

    connection = get_connection()
    connection.execute("DELETE FROM users WHERE id = %s", (representative["id"],))
    connection.execute("DELETE FROM teams WHERE name LIKE '%Dashboard Team'")
    connection.commit()
    connection.close()


def test_dashboard_read_model_returns_empty_for_unassigned_representative():
    assert get_representative_dashboard(-1) == {"teams": []}
