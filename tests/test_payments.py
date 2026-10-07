"""Team payment balances and representative visibility tests."""

from fastapi.testclient import TestClient

from database import get_connection
from dependencies.auth import require_team_representative
from main import app


client = TestClient(app)


def test_admin_records_cash_payment_and_reads_balance():
    connection = get_connection()
    team = connection.execute(
        """
        INSERT INTO teams (name, branch, category)
        VALUES ('Payments Cash Team', 'varonil', 'libre')
        RETURNING id
        """
    ).fetchone()
    connection.commit()
    connection.close()

    initial_balances = client.get("/api/admin/payments/teams")
    assert initial_balances.status_code == 200
    initial_team = next(item for item in initial_balances.json() if item["id"] == team["id"])
    assert initial_team["finance"]["registration_fee"] == 2700
    assert initial_team["finance"]["balance_due"] == 2700

    fee_response = client.patch(
        f"/api/admin/payments/teams/{team['id']}/fee",
        json={"amount": "3000.00"},
    )
    payment_response = client.post(
        f"/api/admin/payments/teams/{team['id']}/payments",
        data={
            "amount": "1200.50",
            "method": "cash",
            "receiver_name": "Mesa de control",
            "reference": "EF-001",
        },
    )
    balances = client.get("/api/admin/payments/teams")

    assert fee_response.status_code == 204
    assert payment_response.status_code == 201
    assert balances.status_code == 200
    payment_team = next(
        item for item in balances.json() if item["id"] == team["id"]
    )
    assert payment_team["finance"]["registration_fee"] == 3000
    assert payment_team["finance"]["paid_amount"] == 1200.5
    assert payment_team["finance"]["balance_due"] == 1799.5
    assert payment_team["finance"]["payments"][0]["method"] == "cash"
    assert payment_team["finance"]["payments"][0]["receiver_name"] == "Mesa de control"

    connection = get_connection()
    connection.execute("DELETE FROM teams WHERE id = %s", (team["id"],))
    connection.commit()
    connection.close()


def test_representative_dashboard_includes_only_own_payment_history():
    connection = get_connection()
    representative = connection.execute(
        """
        INSERT INTO users (email, name, password_hash, role)
        VALUES ('payments-rep@example.test', 'Payments Rep', 'unused', 'team_representative')
        RETURNING id
        """
    ).fetchone()
    assigned = connection.execute(
        """
        INSERT INTO teams (name, branch, category, registration_fee_cents)
        VALUES ('Assigned Payment Team', 'femenil', 'u18', 250000)
        RETURNING id
        """
    ).fetchone()
    hidden = connection.execute(
        """
        INSERT INTO teams (name, branch, category, registration_fee_cents)
        VALUES ('Hidden Payment Team', 'femenil', 'u18', 250000)
        RETURNING id
        """
    ).fetchone()
    connection.execute(
        "INSERT INTO team_representatives (user_id, team_id) VALUES (%s, %s)",
        (representative["id"], assigned["id"]),
    )
    connection.execute(
        """
        INSERT INTO team_payments (team_id, amount_cents, method, receiver_name)
        VALUES (%s, 100000, 'transfer', 'Admin'), (%s, 250000, 'cash', 'Admin')
        """,
        (assigned["id"], hidden["id"]),
    )
    connection.commit()
    connection.close()

    user = {
        "id": representative["id"],
        "role": "team_representative",
        "roles": ["team_representative"],
    }
    app.dependency_overrides[require_team_representative] = lambda: user
    response = client.get("/api/me/representative-dashboard")
    app.dependency_overrides.pop(require_team_representative, None)

    assert response.status_code == 200
    teams = response.json()["teams"]
    assert [team["name"] for team in teams] == ["Assigned Payment Team"]
    assert teams[0]["finance"]["registration_fee"] == 2500
    assert teams[0]["finance"]["paid_amount"] == 1000
    assert teams[0]["finance"]["balance_due"] == 1500
    assert len(teams[0]["finance"]["payments"]) == 1

    connection = get_connection()
    connection.execute(
        "DELETE FROM users WHERE id = %s",
        (representative["id"],),
    )
    connection.execute(
        "DELETE FROM teams WHERE id = ANY(%s)",
        ([assigned["id"], hidden["id"]],),
    )
    connection.commit()
    connection.close()
