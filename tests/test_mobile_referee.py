"""Mobile role access and Bearer assignment isolation without a database."""
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.mark.parametrize("roles", [["referee"], ["player"], ["player", "referee"]])
def test_mobile_roles_can_login_and_restore_session(monkeypatch, roles):
    user = {"id": 73, "name": "Official", "roles": roles}
    monkeypatch.setattr("routes.auth.authenticate_user", lambda *args: user)
    monkeypatch.setattr("routes.auth.create_session", lambda user_id: {
        "token": "native-token", "expires_at": "2026-12-01T00:00:00Z",
    })
    lookup = Mock(return_value=user)
    monkeypatch.setattr("routes.auth.get_authenticated_user", lookup)
    with TestClient(app) as client:
        response = client.post("/api/auth/mobile/login", json={"email": "official@example.com", "password": "supersecret"})
        assert response.status_code == 200
        assert response.json()["user"]["roles"] == roles
        restored = client.get("/api/auth/me", headers={"Authorization": "Bearer native-token"})
        assert restored.json()["id"] == 73
        lookup.assert_called_once_with("native-token")


@pytest.mark.parametrize("user,status", [
    (None, 401),
    ({"id": 73, "roles": ["league_admin"]}, 403),
    ({"id": 73, "roles": ["referee"], "must_change_password": True}, 403),
])
def test_mobile_rejections_do_not_create_sessions(monkeypatch, user, status):
    monkeypatch.setattr("routes.auth.authenticate_user", lambda *args: user)
    create = Mock()
    monkeypatch.setattr("routes.auth.create_session", create)
    with TestClient(app) as client:
        response = client.post("/api/auth/mobile/login", json={"email": "official@example.com", "password": "supersecret"})
        assert response.status_code == status
    create.assert_not_called()


def test_bearer_assignments_are_scoped_to_referee(monkeypatch):
    lookup = Mock(return_value={"id": 73, "roles": ["referee"]})
    games = Mock(return_value=[])
    monkeypatch.setattr("dependencies.auth.get_authenticated_user", lookup)
    monkeypatch.setattr("routes.games.get_games_for_referee", games)
    with TestClient(app) as client:
        response = client.get("/api/games/mine/referee?user_id=99", headers={"Authorization": "Bearer native-token"})
        assert response.status_code == 200
        assert response.json() == []
    lookup.assert_called_once_with("native-token")
    games.assert_called_once_with(73)


def test_player_cannot_read_referee_assignments(monkeypatch):
    monkeypatch.setattr("dependencies.auth.get_authenticated_user", lambda token: {"id": 73, "roles": ["player"]})
    games = Mock()
    monkeypatch.setattr("routes.games.get_games_for_referee", games)
    with TestClient(app) as client:
        assert client.get("/api/games/mine/referee", headers={"Authorization": "Bearer player-token"}).status_code == 403
    games.assert_not_called()
