"""Sign-in, registration and recovery are rate limited per address and account."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from psycopg.errors import UndefinedTable

from database import get_connection
from main import app
from models import UserCreate
from repositories import rate_limits as rate_limit_store
from repositories.users import create_user
from services import rate_limits


client = TestClient(app, base_url="https://testserver")


@pytest.fixture(autouse=True)
def limits_on(monkeypatch):
    """The suite disables limits globally; these tests switch them on."""
    monkeypatch.setattr(rate_limits, "rate_limits_enabled", lambda: True)
    connection = get_connection()
    connection.execute("DELETE FROM auth_rate_limits")
    connection.commit()
    connection.close()
    app.dependency_overrides.clear()
    client.cookies.clear()


def make_user(password="rightsecret"):
    email = f"limits-{uuid4().hex[:10]}@example.test"
    create_user(UserCreate(email=email, name="Limits", password=password, role="referee"))
    return email


def login(email, password, address="198.51.100.1"):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers={"X-Real-IP": address},
    )


def test_repeated_failures_lock_the_account_for_a_while(monkeypatch):
    monkeypatch.setitem(rate_limits.LIMITS, "login_email_failures", (3, 900))
    email = make_user()

    failures = [login(email, "wrongsecret", address=f"198.51.100.{index}") for index in range(3)]
    blocked = login(email, "rightsecret", address="198.51.100.200")

    assert [response.status_code for response in failures] == [401, 401, 401]
    # Even the right password waits: the account had too many failures.
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1
    assert blocked.json()["detail"] == rate_limits.TOO_MANY_ATTEMPTS
    # Another account is not affected.
    assert login(make_user(), "rightsecret").status_code == 200


def test_a_successful_sign_in_does_not_count_against_the_account(monkeypatch):
    monkeypatch.setitem(rate_limits.LIMITS, "login_email_failures", (2, 900))
    email = make_user()
    for _ in range(4):
        assert login(email, "rightsecret").status_code == 200


def test_one_address_is_limited_across_accounts(monkeypatch):
    monkeypatch.setitem(rate_limits.LIMITS, "login_ip", (3, 300))
    attempts = [login(make_user(), "wrongsecret", address="203.0.113.7") for _ in range(4)]

    assert [response.status_code for response in attempts] == [401, 401, 401, 429]
    assert login(make_user(), "rightsecret", address="203.0.113.8").status_code == 200


def test_mobile_sign_in_shares_the_same_limits(monkeypatch):
    monkeypatch.setitem(rate_limits.LIMITS, "login_ip", (1, 300))
    email = make_user()
    payload = {"email": email, "password": "wrongsecret"}
    headers = {"X-Real-IP": "203.0.113.20"}
    assert client.post("/api/auth/mobile/login", json=payload, headers=headers).status_code == 401
    assert client.post("/api/auth/mobile/login", json=payload, headers=headers).status_code == 429


def test_reset_emails_stop_silently_after_the_account_limit(monkeypatch):
    monkeypatch.setitem(rate_limits.LIMITS, "forgot_email", (1, 3600))
    created = []
    monkeypatch.setattr("routes.auth.create_password_reset", lambda email: created.append(email))
    email = make_user()

    first = client.post("/api/auth/forgot-password", json={"email": email})
    second = client.post("/api/auth/forgot-password", json={"email": email})

    assert first.status_code == second.status_code == 202
    # Same answer, so the response never tells whether the email exists...
    assert first.json() == second.json()
    # ...but only the first request created a reset.
    assert created == [email]


def test_registration_and_reset_are_limited_per_address(monkeypatch):
    monkeypatch.setitem(rate_limits.LIMITS, "register_ip", (1, 3600))
    monkeypatch.setitem(rate_limits.LIMITS, "reset_ip", (1, 900))
    headers = {"X-Real-IP": "203.0.113.30"}
    # Invalid on purpose: the attempt is counted before the data is validated.
    form = {"email": "x@example.test", "password": "short", "name": "X", "curp": "X"}
    photo = {"photo": ("photo.png", b"not-checked", "image/png")}

    first = client.post("/api/auth/register/player", data=form, files=photo, headers=headers)
    second = client.post("/api/auth/register/player", data=form, files=photo, headers=headers)
    assert first.status_code == 422
    assert second.status_code == 429

    reset = {"token": "t" * 40, "new_password": "newsecret1"}
    assert client.post("/api/auth/reset-password", json=reset, headers=headers).status_code == 400
    assert client.post("/api/auth/reset-password", json=reset, headers=headers).status_code == 429


def test_counters_store_hashes_not_emails_or_addresses():
    email = make_user()
    login(email, "wrongsecret", address="192.0.2.55")
    connection = get_connection()
    keys = [row["key_hash"] for row in connection.execute("SELECT key_hash FROM auth_rate_limits")]
    connection.close()
    assert keys
    assert all(len(key) == 64 for key in keys)
    assert not any(email in key or "192.0.2.55" in key for key in keys)


def test_a_missing_table_never_blocks_sign_in(monkeypatch):
    class MissingTableConnection:
        def execute(self, *_args, **_kwargs):
            raise UndefinedTable("relation \"auth_rate_limits\" does not exist")

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(rate_limit_store, "get_connection", lambda: MissingTableConnection())
    email = make_user()
    assert login(email, "rightsecret").status_code == 200


def test_limits_are_off_in_the_test_environment(monkeypatch):
    monkeypatch.undo()
    monkeypatch.setenv("APP_ENV", "test")
    assert rate_limits.rate_limits_enabled() is False
    monkeypatch.setenv("APP_ENV", "production")
    assert rate_limits.rate_limits_enabled() is True
    monkeypatch.setenv("AUTH_RATE_LIMITS", "false")
    assert rate_limits.rate_limits_enabled() is False
