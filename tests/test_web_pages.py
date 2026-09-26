"""Smoke tests for server-rendered public and authentication pages."""

import os

from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://flagtastic:flagtastic@localhost:5432/flagtastic"
)

from main import app


client = TestClient(app)


def test_navigation_starts_collapsed_and_remembers_the_user_choice():
    page = client.get("/teams")
    layout = client.get("/static/layout.js")
    styles = client.get("/static/style.css")

    assert page.status_code == 200
    assert layout.status_code == 200
    assert styles.status_code == 200
    assert '<body class="sidebar-collapsed">' in page.text
    assert 'aria-expanded="false"' in page.text
    assert "flagtastic-sidebar-collapsed" in layout.text
    assert "localStorage.setItem" in layout.text
    assert "window.innerWidth <= MOBILE_BREAKPOINT" in layout.text
    assert "setSidebarCollapsed(true, true)" in layout.text
    assert "body.sidebar-collapsed .navigation" in styles.text
    assert "body.sidebar-collapsed .brand-logo" in styles.text
    assert 'id="sidebar-backdrop"' in page.text
    assert "closeMobileSidebar" in layout.text
    assert 'event.key === "Escape"' in layout.text
    assert ".sidebar-backdrop" in styles.text
    assert "position: fixed" in styles.text
    normalized_styles = styles.text.replace("\r\n", "\n")
    assert ".hidden {\n    display: none !important;" in normalized_styles


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


def test_statistics_client_keeps_import_and_official_leaderboard_contract():
    response = client.get("/static/statistics.js")

    assert response.status_code == 200
    assert "submitStatisticsImport" in response.text
    assert "completion_percentage" in response.text
    assert "El Francotirador" in response.text
    assert "profile_photo_url" in response.text
    assert "player_aka" in response.text


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


def test_referee_page_has_reviewed_image_import():
    response = client.get("/referee/games")

    assert response.status_code == 200
    assert 'id="referee-schedule-form"' in response.text
    assert 'accept="image/jpeg,image/png,image/webp"' in response.text
    assert 'id="schedule-review-body"' in response.text
    assert 'id="confirm-schedule"' in response.text
