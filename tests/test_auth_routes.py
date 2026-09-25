"""Tests for authentication HTTP endpoints"""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://flagtastic:flagtastic@localhost:5432/flagtastic"
)

from database import get_connection
from main import app
from models import StaffAccountCreate, UserCreate
from repositories.users import create_staff_account, create_user

client = TestClient(
    app,
    base_url="https://testserver"
    )

@pytest.fixture(autouse=True)
def clean_database():
    client.cookies.clear()

    connection = get_connection()

    connection.execute("DELETE FROM team_representatives")
    connection.execute("DELETE FROM users")

    connection.commit()
    connection.close()

def test_login_creates_http_only_session_cookie():
    created_user = create_user(
        UserCreate(
            email="admin@flagtastic.com",
            name="League admin",
            password="supersecret",
            role="league_admin"
        )
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "ADMIN@FLAGTASTIC.COM",
            "password": "supersecret"
        }
    )

    assert response.status_code == 200
    assert response.json() == created_user

    set_cookie = response.headers["set-cookie"]

    assert "flagtastic_session" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "supersecret" not in response.text

def test_login_rejects_invalid_credentials_without_cookie():
    create_user(
        UserCreate(
            email="admin@flagtastic.com",
            name="League admin",
            password="supersecret",
            role="league_admin"
        )
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@flagtastic.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Correo o contraseña incorrectos"
    }

    assert "set-cookie" not in response.headers
    assert "wrongpassword" not in response.text

def test_login_does_not_reveal_unknown_email():
    response = client.post(
        "/api/auth/login",
        json={
            "email": "missing@flagtastic.com",
            "password": "supersecret"
        }
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Correo o contraseña incorrectos"
    }

    assert "set-cookie" not in response.headers
    assert "missing@flagtastic.com" not in response.text

def test_get_current_authenticated_user():
    created_user = create_user(
        UserCreate(
            email="admin@flagtastic.com",
            name="League admin",
            password="supersecret",
            role="league_admin"
        )
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@flagtastic.com",
            "password": "supersecret"
        }
    )

    assert login_response.status_code == 200

    response = client.get(
        "/api/auth/me"
    )

    assert response.status_code == 200
    assert response.json() == created_user
    assert "password" not in response.text

def test_get_current_user_requires_session_cookie():
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "No autenticado"
    }

def test_get_current_user_rejects_invalid_session_cookie():
    response = client.get(
        "/api/auth/me",
        headers={
        "Cookie": "flagtastic_session=invalid-token"
        }
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "No autenticado"
    }

def test_logout_revokes_session_and_deletes_cookie():
    create_user(
        UserCreate(
            email="admin@flagtastic.com",
            name="League admin",
            password="supersecret",
            role="league_admin"
        )
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@flagtastic.com",
            "password":"supersecret"
        }
    )

    assert login_response.status_code == 200
    
    logout_response = client.post(
        "/api/auth/logout"
    )

    assert logout_response.status_code == 204

    set_cookie = logout_response.headers["set-cookie"]

    assert "flagtastic_session="  in set_cookie
    assert "Max-Age=0" in set_cookie

    current_user_response = client.get("/api/auth/me")

    assert current_user_response.status_code == 401
    assert current_user_response.json() == {
        "detail": "No autenticado"
    }

def test_logout_without_session_is_idempotent():
    response = client.post("/api/auth/logout")

    assert response.status_code == 204

    set_cookie = response.headers["set-cookie"]

    assert "flagtastic_session" in set_cookie
    assert "Max-Age=0" in set_cookie


def test_staff_must_change_initial_password_before_authorized_access():
    create_staff_account(StaffAccountCreate(
        email="president@flagtastic.com",
        name="League President",
        password="initialsecret",
        roles={"league_admin", "referee"}
    ))

    login_response = client.post(
        "/api/auth/login",
        json={"email": "president@flagtastic.com", "password": "initialsecret"}
    )
    assert login_response.status_code == 200
    assert login_response.json()["must_change_password"] is True

    change_response = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "initialsecret",
            "new_password": "replacementsecret"
        }
    )
    assert change_response.status_code == 204

    client.cookies.clear()
    assert client.post(
        "/api/auth/login",
        json={"email": "president@flagtastic.com", "password": "initialsecret"}
    ).status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"email": "president@flagtastic.com", "password": "replacementsecret"}
    ).status_code == 200
