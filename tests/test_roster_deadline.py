"""Exact server-time cutoff and authorization coverage for roster writes."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from dependencies import auth
from main import app
from repositories import teams
from services import roster_policy


REPRESENTATIVE = {"id": 42, "roles": ["team_representative"]}


def freeze(monkeypatch, instant):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz)

    monkeypatch.setattr(roster_policy, "datetime", Clock)


@pytest.mark.parametrize("instant,closed", [
    ("2026-10-16T05:59:59.999999+00:00", False),
    ("2026-10-16T06:00:00+00:00", True),
    ("2026-10-17T06:00:00+00:00", True),
])
def test_mexico_city_midnight_boundary(monkeypatch, instant, closed):
    freeze(monkeypatch, datetime.fromisoformat(instant))
    assert roster_policy.roster_is_closed() is closed
    assert roster_policy.ROSTER_CLOSES_AT.isoformat() == "2026-10-16T00:00:00-06:00"


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_representative_writes_close_at_midnight_but_admins_keep_access(monkeypatch, method):
    monkeypatch.setattr(auth, "user_represents_team", lambda *_: True)
    request = Request({"type": "http", "method": method})
    freeze(monkeypatch, datetime(2026, 10, 16, 5, 59, 59, tzinfo=timezone.utc))
    assert auth.require_team_manager(request, 1, REPRESENTATIVE) == REPRESENTATIVE
    freeze(monkeypatch, datetime(2026, 10, 16, 6, tzinfo=timezone.utc))
    with pytest.raises(HTTPException) as error:
        auth.require_team_manager(request, 1, REPRESENTATIVE)
    assert error.value.status_code == 403
    for admin in ({"role": "league_admin"}, {"roles": ["team_representative", "league_admin"]}):
        assert auth.require_team_manager(request, 1, admin) == admin
    assert auth.require_team_manager(Request({"type": "http", "method": "GET"}), 1, REPRESENTATIVE) == REPRESENTATIVE


@pytest.mark.parametrize("method,path", [
    ("POST", "/api/teams/1/players"),
    ("POST", "/api/teams/1/players/registered"),
    ("POST", "/api/teams/1/players/import"),
    ("PUT", "/api/teams/1/players/2/photo"),
    ("PATCH", "/api/teams/1/players/2"),
    ("DELETE", "/api/teams/1/players/2"),
    ("PUT", "/api/teams/1/logo"),
    ("PATCH", "/api/teams/1/staff"),
])
def test_each_write_endpoint_enforces_cutoff_before_mutating(monkeypatch, method, path):
    app.dependency_overrides.clear()
    app.dependency_overrides[auth.require_authenticated_user] = lambda: REPRESENTATIVE
    monkeypatch.setattr(auth, "user_represents_team", lambda *_: True)
    freeze(monkeypatch, datetime(2026, 10, 16, 6, tzinfo=timezone.utc))
    response = TestClient(app).request(method, path)
    assert response.status_code == 403, response.text
    assert response.json()["detail"] == roster_policy.ROSTER_CLOSED_MESSAGE


@pytest.mark.parametrize("is_admin,closed,can_manage", [
    (False, True, False), (True, True, True), (False, False, True),
])
def test_team_detail_hides_changes_but_keeps_roster_visible(monkeypatch, is_admin, closed, can_manage):
    connection = MagicMock()
    connection.execute.return_value.fetchone.side_effect = [
        {"id": 1, "name": "Test", "has_logo": False}, {"exists": 1},
    ]
    connection.execute.return_value.fetchall.return_value = [{"id": 2, "name": "Player"}]
    monkeypatch.setattr(teams, "get_connection", lambda: connection)
    freeze(monkeypatch, datetime(2026, 10, 16, 6 if closed else 5, tzinfo=timezone.utc))
    detail = teams.get_team_roster_detail(1, user_id=42, is_admin=is_admin)
    assert detail["can_manage"] is can_manage
    assert detail["roster_closed"] is closed
    assert detail["players"][0]["name"] == "Player"
    assert detail["roster_closes_at"] == "2026-10-16T00:00:00-06:00"


def test_dual_role_representative_cannot_bypass_via_player_join(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[auth.require_player] = lambda: {
        "id": 42, "player_id": 2, "roles": ["player", "team_representative"],
    }
    freeze(monkeypatch, datetime(2026, 10, 16, 6, tzinfo=timezone.utc))
    response = TestClient(app).post("/api/me/teams/1", json={"jersey_number": 3})
    assert response.status_code == 403


def test_deadline_never_grants_access_to_unassigned_representative(monkeypatch):
    monkeypatch.setattr(auth, "user_represents_team", lambda *_: False)
    freeze(monkeypatch, datetime(2026, 10, 15, tzinfo=timezone.utc))
    with pytest.raises(HTTPException) as error:
        auth.require_team_manager(Request({"type": "http", "method": "POST"}), 1, REPRESENTATIVE)
    assert error.value.status_code == 403
