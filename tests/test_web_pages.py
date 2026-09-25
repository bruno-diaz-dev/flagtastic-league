"""Smoke tests for server-rendered public and authentication pages."""

import os

from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://flagtastic:flagtastic@localhost:5432/flagtastic"
)

from main import app


client = TestClient(app)


def test_login_page_renders_protected_password_form():
    response = client.get("/login")

    assert response.status_code == 200
    assert 'id="login-form"' in response.text
    assert 'name="email"' in response.text
    assert 'name="password"' in response.text
    assert 'type="password"' in response.text
    assert 'src="/static/login.js' in response.text


def test_statistics_page_renders_division_filters():
    response = client.get("/statistics")

    assert response.status_code == 200
    assert 'id="leaderboard-form"' in response.text
    assert 'name="branch"' in response.text
    assert 'name="category"' in response.text
    assert 'id="leaderboards"' in response.text
    assert 'id="statistics-import-form"' in response.text
    assert "Descargar plantilla Excel" in response.text
    assert 'src="/static/statistics.js' in response.text


def test_player_registration_page_is_available():
    response = client.get("/register")

    assert response.status_code == 200
    assert "Crear cuenta de jugador" in response.text
    assert 'src="/static/register.js' in response.text
    assert 'type="password"' in response.text
    assert 'name="aka"' in response.text
    assert 'name="photo"' in response.text
    assert 'type="file"' in response.text
    assert 'accept="image/jpeg,image/png,image/webp"' in response.text
    assert 'name="photo" type="file"' in response.text


def test_player_dashboard_page_is_available():
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Mi dashboard" in response.text
    assert 'src="/static/dashboard.js' in response.text


def test_team_roster_has_a_dedicated_page():
    response = client.get("/teams/123/roster")

    assert response.status_code == 200
    assert 'id="roster-page"' in response.text
    assert 'data-team-id="123"' in response.text
    assert 'src="/static/roster.js' in response.text
    assert "Volver a equipos" in response.text


def test_user_administration_page_is_available():
    response = client.get("/admin/users")

    assert response.status_code == 200
    assert "Usuarios y roles" in response.text
    assert 'src="/static/admin_users.js' in response.text
