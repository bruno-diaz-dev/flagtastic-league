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
    assert ".content > section" in styles.text
    assert "max-width: 100%" in styles.text
    normalized_styles = styles.text.replace("\r\n", "\n")
    assert ".hidden {\n    display: none !important;" in normalized_styles


def test_login_page_renders_protected_password_form():
    response = client.get("/login")
    script = client.get("/static/login.js")

    assert response.status_code == 200
    assert 'id="login-form"' in response.text
    assert 'name="email"' in response.text
    assert 'name="password"' in response.text
    assert 'type="password"' in response.text
    assert 'src="/static/login.js' in response.text
    assert 'roles.includes("referee")' in script.text
    assert '"/referee/games"' in script.text


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
    assert 'name="privacy_acknowledgement"' in response.text
    assert 'href="/privacy"' in response.text


def test_player_dashboard_page_is_available():
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Mi dashboard" in response.text
    assert 'rel="icon" type="image/jpeg"' in response.text
    assert 'href="/static/assets/flagtastic.jpeg' in response.text
    assert 'src="/static/dashboard.js' in response.text
    assert 'id="dashboard-photo-placeholder"' in response.text
    assert 'id="join-team-branch"' in response.text
    assert 'id="join-team-category"' in response.text
    assert 'id="join-team-results"' in response.text

    script = client.get("/static/dashboard.js")
    stylesheet = client.get("/static/style.css")
    assert "profilePhoto.onerror" in script.text
    assert "renderTeamOptions" in script.text
    assert "teamBranchFilter.addEventListener" in script.text
    assert "teamCategoryFilter.addEventListener" in script.text
    assert "#profile-form" in stylesheet.text
    assert "grid-template-columns: minmax(0, 1fr)" in stylesheet.text


def test_representative_dashboard_page_is_available():
    response = client.get("/representative-dashboard")
    assert response.status_code == 200
    assert "Mi dashboard de representante" in response.text
    assert 'id="representative-summary"' in response.text
    assert 'src="/static/representative_dashboard.js' in response.text

    script = client.get("/static/representative_dashboard.js")
    assert "renderRepresentativeSummary" in script.text
    assert "Récord combinado" in script.text
    assert "Mejor posición" in script.text

    navigation = client.get("/teams").text
    assert 'id="representative-dashboard-link"' in navigation
    assert 'href="/privacy"' in navigation


def test_integral_privacy_notice_is_public():
    response = client.get("/privacy")

    assert response.status_code == 200
    assert "Aviso de privacidad integral" in response.text
    assert "Datos personales tratados" in response.text
    assert "Derechos ARCO" in response.text
    assert "Personas menores de edad" in response.text
    assert "cookies publicitarias" in response.text


def test_public_player_profile_page_is_available():
    response = client.get("/players/123")

    assert response.status_code == 200
    assert 'data-player-id="123"' in response.text
    assert 'id="public-player-stats"' in response.text
    assert 'src="/static/player_profile.js' in response.text


def test_team_roster_has_a_dedicated_page():
    response = client.get("/teams/123/roster")
    script = client.get("/static/roster.js")

    assert response.status_code == 200
    assert 'id="roster-page"' in response.text
    assert 'data-team-id="123"' in response.text
    assert 'src="/static/roster.js' in response.text
    assert "Volver a equipos" in response.text
    assert 'id="team-logo-form"' in response.text
    assert 'id="team-staff-form"' in response.text
    assert 'accept="image/jpeg,image/png,image/webp"' in response.text
    assert 'class="form-panel team-scope-manager-only"' in response.text
    assert 'id="registered-player-search"' in response.text
    assert 'id="registered-player-results"' in response.text
    assert "searchRegisteredPlayers" in script.text
    assert "addRegisteredPlayer" in script.text
    assert "Edad cumplida" in response.text

    assert "roster-photo-form team-scope-manager-only" in script.text
    assert "uploadRosterPlayerPhoto" in script.text
    assert 'team.can_manage === true' in script.text
    assert "updateRosterPlayer" in script.text
    assert "deactivateRosterPlayer" in script.text


def test_collection_images_are_loaded_lazily():
    scripts = [
        client.get("/static/teams.js").text,
        client.get("/static/games.js").text,
        client.get("/static/standings.js").text,
        client.get("/static/statistics.js").text,
        client.get("/static/representative_dashboard.js").text,
        client.get("/static/roster.js").text
    ]
    assert all('loading="lazy"' in script for script in scripts)
    assert all('decoding="async"' in script for script in scripts)


def test_team_change_center_has_a_dedicated_page():
    response = client.get("/teams/123/manage")
    directory_script = client.get("/static/teams.js")
    management_script = client.get("/static/team_manage.js")

    assert response.status_code == 200
    assert 'id="team-management-page"' in response.text
    assert 'data-team-id="123"' in response.text
    assert 'id="team-name-form"' in response.text
    assert 'id="team-status-form"' in response.text
    assert 'id="team-representative-form"' in response.text
    assert 'id="delete-managed-team"' in response.text
    assert 'src="/static/team_manage.js' in response.text

    assert 'href="/teams/${team.id}/manage"' in directory_script.text
    assert "data-update-team-status" not in directory_script.text
    assert 'const branchOrder = ["varonil", "femenil", "mixto"]' in directory_script.text

    assert management_script.status_code == 200
    assert "updateTeamStatus" in management_script.text
    assert "updateTeamName" in management_script.text
    assert "assignTeamRepresentative" in management_script.text
    assert "removeTeamRepresentative" in management_script.text


def test_user_administration_page_is_available():
    response = client.get("/admin/users")

    assert response.status_code == 200
    assert "Usuarios y roles" in response.text
    assert 'id="admin-user-name-filter"' in response.text
    assert 'id="admin-users-count"' in response.text
    assert 'src="/static/admin_users.js' in response.text

    script = client.get("/static/admin_users.js")
    assert "delete-user-button" in script.text
    assert "deleteAdminUser" in script.text
    assert "normalizedSearchText" in script.text
    assert "user.display_name, user.name, user.aka" in script.text


def test_public_player_links_are_rendered_by_roster_and_leaderboards():
    roster_script = client.get("/static/roster.js")
    statistics_script = client.get("/static/statistics.js")

    assert 'href="/players/${player.id}"' in roster_script.text
    assert 'href="/players/${leader.player_id}"' in statistics_script.text


def test_referee_page_has_reviewed_image_import():
    response = client.get("/referee/games")

    assert response.status_code == 200
    assert "Mi dashboard de arbitraje" in response.text
    assert 'id="referee-summary"' in response.text
    assert 'id="referee-games"' in response.text
    assert 'id="referee-schedule-form"' in response.text
    assert 'accept="image/jpeg,image/png,image/webp"' in response.text
    assert 'id="schedule-review-body"' in response.text
    assert 'id="confirm-schedule"' in response.text
    assert 'id="referee-dashboard-photo-panel"' in response.text
    assert 'href="/referees"' in response.text

    script = client.get("/static/referee_games.js")
    assert "renderRefereeSummary" in script.text
    assert "Asignaciones pendientes" in script.text
    assert "Historial de arbitrajes" in script.text
    assert "Planilla arbitral" in script.text
    assert 'href="/games/${game.id}"' in script.text
    assert "requestMissingRefereePhoto" in script.text


def test_registered_user_referee_roster_page_is_available():
    response = client.get("/referees")

    assert response.status_code == 200
    assert "Planilla de árbitros" in response.text
    assert 'id="referee-roster"' in response.text
    assert 'id="referee-photo-form"' in response.text
    assert 'src="/static/referees.js' in response.text

    layout = client.get("/static/layout.js")
    assert "refereeRosterLink" in layout.text


def test_games_page_accepts_image_xlsx_and_csv_schedule_imports():
    response = client.get("/games")

    assert response.status_code == 200
    assert 'id="game-schedule-import-form"' in response.text
    assert 'accept="image/jpeg,image/png,image/webp,.xlsx,.csv"' in response.text
    assert 'id="game-schedule-review-body"' in response.text
    assert 'id="confirm-game-schedule"' in response.text

    script = client.get("/static/games.js")
    assert "analyzeGameSchedule" in script.text
    assert "confirmGameSchedule" in script.text
