import os

import pytest

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://flagtastic:flagtastic@localhost:5432/flagtastic"
)

from database import get_connection
from models import UserCreate
from repositories.sessions import (
    create_session,
    get_active_session,
    revoke_session
)
from repositories.users import create_user

@pytest.fixture(autouse=True)
def clean_database():
    connection = get_connection()

    connection.execute(
        "DELETE FROM sessions"
    )

    connection.execute(
        "DELETE FROM team_representatives"
    )

    connection.execute(
        "DELETE FROM users"
    )

    connection.commit()
    connection.close()

def test_create_sessions_store_only_token_hash():
    user = create_user(
        UserCreate(
            email="admin@flagtastic.com",
            name="League admin",
            password="supersecret",
            role="league_admin"
        )
    )

    session = create_session(user["id"])

    connection = get_connection()
    stored_session = connection.execute(
        """
        SELECT
            user_id,
            token_hash,
            expires_at,
            created_at,
            revoked_at
        FROM sessions
        WHERE id = %s
        """,
        (session["id"],)
    ).fetchone()
    connection.close()

    assert session["user_id"] == user["id"]
    assert isinstance(session["token"], str)
    assert session["token"]
    assert "token_hash" not in session

    assert stored_session["user_id"] == user["id"]
    assert stored_session["token_hash"] != session["token"]
    assert len(stored_session["token_hash"]) == 64
    assert stored_session["expires_at"] > stored_session["created_at"]
    assert stored_session["revoked_at"] is None

def test_get_active_session():
    user = create_user(
        UserCreate(
            email="admin@flagtastic.com",
            name="League admin",
            password="supersecret",
            role="league_admin"
        )
    )

    created_session = create_session(user["id"])

    active_session = get_active_session(
        created_session["token"]
    )

    assert active_session["id"] == created_session["id"]
    assert active_session["user_id"] == user["id"]
    assert active_session["revoked_at"] is None
    assert "token" not in active_session
    assert "token_hash" not in active_session

def test_unknown_token_does_not_return_session():
    active_session = get_active_session(
        "token-that-does-not-exist"
    )

    assert active_session is None

def test_expired_session_is_not_active():
    user = create_user(
        UserCreate(
            email="admin@flagtastic.com",
            name="League admin",
            password="supersecret",
            role="league_admin"
        )
    )

    created_session = create_session(user["id"])

    connection = get_connection()
    connection.execute(
        """
        UPDATE sessions
        SET
            created_at = NOW() - INTERVAL '2 days',
            expires_at = NOW() - INTERVAL '1 day'
        WHERE id = %s
        """,
        (created_session["id"],)
    )
    connection.commit()
    connection.close()

    active_session = get_active_session(
        created_session["token"]
    )

    assert active_session is None

def test_revoked_session_is_not_active():
    user = create_user(
        UserCreate(
            email="admin@flagtastic.com",
            name="League admin",
            password="supersecret",
            role="league_admin"
        )
    )

    created_session = create_session(user["id"])

    revoked = revoke_session(
        created_session["token"]
    )

    active_session = get_active_session(
        created_session["token"]
    )

    assert revoked is True
    assert active_session is None

def test_revoking_session_twice_return_false():
    user = create_user(
        UserCreate(
            email="admin@flagtastic.com",
            name="League Admin",
            password="supersecret",
            role="league_admin"
        )
    )

    created_session = create_session(user["id"])

    first_revocation = revoke_session(
        created_session["token"]
    )

    second_revocation = revoke_session(
        created_session["token"]
    )

    assert first_revocation is True
    assert second_revocation is False