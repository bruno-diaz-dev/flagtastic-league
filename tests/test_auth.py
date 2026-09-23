"""Tests for credential authentication and session-based identity."""

import os

import pytest

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://flagtastic:flagtastic@localhost:5432/flagtastic"
)

from database import get_connection
from models import LoginRequest, UserCreate
from repositories.users import create_user
from repositories.sessions import create_session
from services.auth import (
    authenticate_user,
    get_authenticated_user
)


@pytest.fixture(autouse=True)
def clean_database():
    connection = get_connection()

    connection.execute(
        """
        DELETE FROM team_representatives
        """
    )

    connection.execute(
        """
        DELETE FROM users
        """
    )

    connection.commit()
    connection.close()

def test_authenticate_user_with_valid_credentials():
    create_user(
        UserCreate(
            email="admin@flagtastic.com",
            name="League Admin",
            password="supersecret",
            role="league_admin"
        )
    )

    authenticated_user = authenticate_user(
        "ADMIN@FLAGTASTIC.COM",
        "supersecret"
    )

    assert authenticated_user == {
        "id": authenticated_user["id"],
        "email": "admin@flagtastic.com",
        "name": "League Admin",
        "role": "league_admin",
        "status": "active"
    }

def test_authenticate_user_with_invalid_password():
    create_user(
        UserCreate(
            email="admin@flagtastic.com",
            name="League Admin",
            password="supersecret",
            role="league_admin"
        )
    )

    authenticated_user = authenticate_user(
        "admin@flagtastic.com",
        "wrongpassword"
    )

    assert authenticated_user is None

def test_authenticate_user_with_unknown_email():
    authenticated_user = authenticate_user(
        "missing@flagtastic.com",
        "supersecret"
    )

    assert authenticated_user is None

def test_inactive_user_cannot_authenticate():
    created_user = create_user(
        UserCreate(
            email="admin@flagtastic.com",
            name="League Admin",
            password="supersecret",
            role="league_admin"
        )
    )

    connection = get_connection()

    connection.execute(
        """
        UPDATE users
        SET status = 'inactive'
        WHERE id = %s
        """,
        (created_user["id"],)
    )
    connection.commit()
    connection.close()

    authenticated_user = authenticate_user(
        "admin@flagtastic.com",
        "supersecret"
    )

    assert authenticated_user is None

def test_get_authenticated_user_from_active_session():
    created_user = create_user(
        UserCreate(
            email="admin@flagtastic.com",
            name="League admin",
            password="supersecret",
            role="league_admin"
        )
    )

    session = create_session(
        created_user["id"]
    )

    authenticated_user = get_authenticated_user(
        session["token"]
    )

    assert authenticated_user == created_user
    assert "password_hash" not in authenticated_user

def test_inactive_user_session_does_not_authenticate():
    created_user = create_user(
        UserCreate(
            email="admin@flagtastic.com",
            name="League admin",
            password="supersecret",
            role="league_admin"
        )
    )

    session = create_session(
        created_user["id"]
    )

    connection = get_connection()
    connection.execute(
        """
        UPDATE users
        SET status = 'inactive'
        WHERE id = %s
        """,
        (created_user["id"],)
    )
    connection.commit()
    connection.close()

    authenticated_user = get_authenticated_user(
        session["token"]
    )

    assert authenticated_user is None

def test_login_request_normalizes_email_and_hides_password():
    login = LoginRequest(
        email=" ADMIN@FLAGTASTIC.COM ",
        password="supersecret"
    )

    assert login.email == "admin@flagtastic.com"
    assert login.password.get_secret_value() == "supersecret"
    assert "supersecret" not in repr(login)
    