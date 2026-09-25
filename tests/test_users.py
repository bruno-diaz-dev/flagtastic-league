import os

import pytest
from psycopg.errors import UniqueViolation
from pydantic import ValidationError

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://flagtastic:flagtastic@localhost:5432/flagtastic"
)

from database import get_connection
from models import UserCreate
from repositories.users import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_credentials_by_email,
    verify_password
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

def test_create_user():
    user = UserCreate(
        email="ADMIN@FLAGTASTIC.COM",
        name="League Admin",
        password="SuperSecret",
        role="league_admin"
    )

    created_user = create_user(user)

    assert created_user["email"] == "admin@flagtastic.com"
    assert created_user["name"] == "League Admin"
    assert created_user["role"] == "league_admin"
    assert created_user["status"] == "active"

    assert "id" in created_user
    assert "password" not in created_user
    assert "password_hash" not in created_user

def test_user_password_is_hashed_and_can_be_verified():
    user = UserCreate(
        email="admin@flagtastic.com",
        name="League Admin",
        password="supersecret",
        role="league_admin"
    )

    create_user(user)

    credentials = get_user_credentials_by_email(
        "admin@flagtastic.com"
    )

    assert credentials is not None
    assert credentials["password_hash"] != "supersecret"
    assert verify_password(
        "supersecret",
        credentials["password_hash"]
    )
    assert not verify_password(
        "wrongpassword",
        credentials["password_hash"]
    )

def test_get_user_by_email_does_not_expose_password_has():
    user = UserCreate(
        email="admin@flagtastic.com",
        name="League Admin",
        password="supersecret",
        role="league_admin"
    )

    create_user(user)

    found_user = get_user_by_email(
        "ADMIN@FLAGTASTIC.COM"
    )

    assert found_user is not None
    assert found_user["email"] == "admin@flagtastic.com"
    assert found_user["name"] == "League Admin"
    assert found_user["role"] == "league_admin"
    assert found_user["status"] == "active"
    assert "password_hash" not in found_user

def test_cannot_create_duplicated_user_email():
    user = UserCreate(
        email="admin@flagtastic.com",
        name="League Admin",
        password="supersecret",
        role="league_admin"
    )

    create_user(user)

    with pytest.raises(UniqueViolation):
        create_user(user)

def test_cannot_create_user_with_invalid_role():
    with pytest.raises(ValidationError):
        UserCreate(
            email="admin@flagtastic.com",
            name="League Admin",
            password="supersecret",
            role="super_admin"
        )

def test_cannot_create_user_with_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(
            email="not-an-email",
            name="League Admin",
            password="supersecret",
            role="league_admin"
        )

def test_get_user_by_email_returns_none_when_user_does_not_exist():
    user = get_user_by_email("missing@flagtastic.com")

    assert user is None

def test_get_user_credentials_returns_none_when_user_does_not_exist():
    credentials = get_user_credentials_by_email(
        "missing@flagtastic.com"
    )

    assert credentials is None

def test_user_role_is_normalized():
    user = UserCreate(
        email="admin@flagtastic.com",
        name="League Admin",
        password="supersecret",
        role="LEAGUE_ADMIN"
    )

    assert user.role == "league_admin"

def test_get_user_by_id_does_not_expose_password_hash():
    created_user = create_user(
        UserCreate(
            email="admin@flagtastic.com",
            name="League admin",
            password="supersecret",
            role="league_admin"
        )
    )

    user = get_user_by_id(
        created_user["id"]
    )

    assert user == {
        "id": created_user["id"],
            "email": "admin@flagtastic.com",
            "name": "League admin",
            "aka": None,
            "display_name": "League admin",
            "role": "league_admin",
            "roles": ["league_admin"],
            "status": "active"
        }

    assert "password_hash" not in user

def test_get_user_by_id_returns_none_when_user_does_not_exist():
    user = get_user_by_id(9999)

    assert user is None
"""Repository and validation tests for application users."""
