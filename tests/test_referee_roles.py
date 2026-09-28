"""Cumulative-role and private referee-assignment HTTP tests."""

from uuid import uuid4

from fastapi.testclient import TestClient

from main import app
from models import UserCreate
from repositories.users import create_user


client = TestClient(app, base_url="https://testserver")
PROFILE_PNG = b"\x89PNG\r\n\x1a\nreferee-profile"


def login(email, password="supersecret"):
    """Replace the current browser session with the selected account."""
    client.cookies.clear()
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )


def test_admin_player_referee_keeps_each_permission(monkeypatch):
    """Granting administrative duties must not hide player capabilities."""
    app.dependency_overrides.clear()
    suffix = uuid4().hex[:10]
    admin_email = f"role-admin-{suffix}@example.test"
    player_email = f"role-player-{suffix}@example.test"

    admin = create_user(UserCreate(
        email=admin_email,
        name="Role Administrator",
        password="supersecret",
        role="league_admin"
    ))
    registration = client.post(
        "/api/auth/register/player",
        data={
            "email": player_email,
            "password": "supersecret",
            "name": "Player Referee",
            "curp": f"REF{suffix.upper()}00000"[:18],
            "age": "28"
        },
        files={"photo": ("profile.png", PROFILE_PNG, "image/png")}
    )
    assert registration.status_code == 201
    player = registration.json()

    assert login(admin_email).status_code == 200
    role_update = client.put(
        f"/api/admin/users/{player['id']}/roles",
        json={"roles": ["league_admin", "player", "referee"]}
    )
    assert role_update.status_code == 200
    assert set(role_update.json()["roles"]) == {
        "league_admin", "player", "referee"
    }

    # A fresh login proves roles are loaded from persistence, not stale UI state.
    assert login(player_email).status_code == 200
    assert client.get("/api/me/dashboard").status_code == 200
    assert client.get("/api/admin/users").status_code == 200
    assert client.get("/api/games/mine/referee").status_code == 200

    # Referee self-service follows cumulative permissions, not the legacy
    # primary role, so multi-role officials can maintain AKA and photo.
    profile = client.get("/api/referees/me")
    assert profile.status_code == 200
    aka_update = client.patch("/api/referees/me", json={"aka": "Brucie"})
    assert aka_update.status_code == 200
    assert aka_update.json()["display_name"] == "Brucie"
    photo_update = client.put(
        "/api/referees/me/photo",
        files={"file": ("profile.png", PROFILE_PNG, "image/png")}
    )
    assert photo_update.status_code == 204

    # OCR matching and the referee directory both follow cumulative roles.
    monkeypatch.setattr(
        "routes.games.parse_referee_schedule_image",
        lambda content, games, referees: {
            "candidate_ids": [referee["id"] for referee in referees]
        }
    )
    analysis = client.post(
        "/api/games/referee-schedule/analyze",
        files={"file": ("rol.png", PROFILE_PNG, "image/png")}
    )
    assert analysis.status_code == 200
    assert player["id"] in analysis.json()["candidate_ids"]
    assert admin["id"] != player["id"]


def test_referee_sees_only_assigned_games(monkeypatch):
    """A referee schedule contains assignments for that account only."""
    app.dependency_overrides.clear()
    suffix = uuid4().hex[:10]
    admin_email = f"schedule-admin-{suffix}@example.test"
    referee_email = f"schedule-referee-{suffix}@example.test"
    other_email = f"schedule-other-{suffix}@example.test"

    admin = create_user(UserCreate(
        email=admin_email, name="Schedule Admin", password="supersecret",
        role="league_admin"
    ))
    referee = create_user(UserCreate(
        email=referee_email, name="Assigned Referee", password="supersecret",
        role="referee"
    ))
    down_judge = create_user(UserCreate(
        email=f"down-{suffix}@example.test", name="Assigned Down Judge",
        password="supersecret", role="referee"
    ))
    create_user(UserCreate(
        email=other_email, name="Other User", password="supersecret",
        role="team_representative"
    ))

    assert login(admin_email).status_code == 200
    home = client.post(
        "/api/teams",
        json={"name": f"Home {suffix}", "branch": "mixto", "category": "libre"}
    ).json()
    away = client.post(
        "/api/teams",
        json={"name": f"Away {suffix}", "branch": "mixto", "category": "libre"}
    ).json()
    game = client.post(
        "/api/games",
        json={
            "home_team_id": home["id"], "away_team_id": away["id"],
            "week": 2, "field_number": 4
        }
    ).json()

    # OCR returns reviewable proposals; it cannot write until confirmation.
    monkeypatch.setattr(
        "routes.games.parse_referee_schedule_image",
        lambda content, games, referees: {
            "raw_text": "Campo 6 Home Away Assigned Referee",
            "proposals": [{
                "game_id": game["id"],
                "game_label": "J2: Home vs Away",
                "field_number": 6,
                "officials": [{
                    "user_id": referee["id"],
                    "name": referee["name"],
                    "position": "referee"
                }],
                "source_text": "Campo 6 Home Away Assigned Referee"
            }]
        }
    )
    analysis = client.post(
        "/api/games/referee-schedule/analyze",
        files={"file": ("rol.png", PROFILE_PNG, "image/png")}
    )
    assert analysis.status_code == 200
    assert analysis.json()["proposals"][0]["field_number"] == 6

    incomplete = client.post(
        "/api/games/referee-schedule/confirm",
        json={"assignments": [{
            "game_id": game["id"],
            "field_number": 6,
            "officials": [
                {"user_id": referee["id"], "position": "referee"}
            ]
        }]}
    )
    assert incomplete.status_code == 409
    assert incomplete.json()["detail"] == "Referee y Down Judge son obligatorios"

    confirmation = client.post(
        "/api/games/referee-schedule/confirm",
        json={"assignments": [{
            "game_id": game["id"],
            "field_number": 6,
            "officials": [
                {"user_id": referee["id"], "position": "referee"},
                {"user_id": down_judge["id"], "position": "down_judge"}
            ]
        }]}
    )
    assert confirmation.status_code == 200

    assignment = client.put(
        f"/api/games/{game['id']}/referees/{referee['id']}",
        json={"position": "referee"}
    )
    assert assignment.status_code == 201
    assert assignment.json()["assigned_by"] == admin["id"]

    # A last-minute replacement occupies the same slot without leaving the
    # previous referee attached to the game.
    replacement = create_user(UserCreate(
        email=f"replacement-{suffix}@example.test",
        name="Replacement Referee",
        password="supersecret",
        role="referee"
    ))
    replacement_response = client.put(
        f"/api/games/{game['id']}/referees/{replacement['id']}",
        json={"position": "referee"}
    )
    assert replacement_response.status_code == 201
    assigned = client.get(f"/api/games/{game['id']}/referees").json()
    referee_slots = [item for item in assigned if item["position"] == "referee"]
    assert [item["id"] for item in referee_slots] == [replacement["id"]]

    assert login(referee_email).status_code == 200
    schedule = client.get("/api/games/mine/referee")
    assert schedule.status_code == 200
    assert schedule.json() == []
    assert client.get(f"/api/games/{game['id']}/referees").status_code == 403

    assert login(replacement["email"]).status_code == 200
    replacement_schedule = client.get("/api/games/mine/referee")
    assert [item["id"] for item in replacement_schedule.json()] == [game["id"]]
    assert replacement_schedule.json()[0]["field_number"] == 6
    assert client.get(f"/api/games/{game['id']}/referees").status_code == 403

    assert login(other_email).status_code == 200
    assert client.get("/api/games/mine/referee").status_code == 403


def test_authenticated_users_see_referee_roster_and_referee_uploads_photo():
    app.dependency_overrides.clear()
    suffix = uuid4().hex[:10]
    referee_email = f"roster-referee-{suffix}@example.test"
    viewer_email = f"roster-viewer-{suffix}@example.test"
    referee = create_user(UserCreate(
        email=referee_email, name="Roster Referee", password="supersecret",
        role="referee"
    ))
    create_user(UserCreate(
        email=viewer_email, name="Registered Viewer", password="supersecret",
        role="team_representative"
    ))

    client.cookies.clear()
    assert client.get("/api/referees").status_code == 401
    assert login(viewer_email).status_code == 200
    before = client.get("/api/referees")
    assert before.status_code == 200
    listed = next(item for item in before.json() if item["id"] == referee["id"])
    assert listed["profile_photo_url"] is None
    assert "email" not in listed
    assert client.put(
        "/api/referees/me/photo",
        files={"file": ("profile.png", PROFILE_PNG, "image/png")}
    ).status_code == 403

    assert login(referee_email).status_code == 200
    assert client.get("/api/referees/me").json()["profile_photo_url"] is None
    upload = client.put(
        "/api/referees/me/photo",
        files={"file": ("profile.png", PROFILE_PNG, "image/png")}
    )
    assert upload.status_code == 204
    profile = client.get("/api/referees/me").json()
    assert profile["profile_photo_url"].startswith("/media/profiles/")
    assert client.get(profile["profile_photo_url"]).content == PROFILE_PNG


def test_referee_can_set_aka_used_by_directory():
    """A referee AKA becomes the public display name used for schedule matching."""
    app.dependency_overrides.clear()
    suffix = uuid4().hex[:10]
    referee_email = f"aka-referee-{suffix}@example.test"
    referee = create_user(UserCreate(
        email=referee_email,
        name="Legal Referee Name",
        password="supersecret",
        role="referee"
    ))

    assert login(referee_email).status_code == 200
    update = client.patch("/api/referees/me", json={"aka": "Central"})
    assert update.status_code == 200
    assert update.json()["aka"] == "Central"
    assert update.json()["display_name"] == "Central"

    roster = client.get("/api/referees")
    assert roster.status_code == 200
    listed = next(item for item in roster.json() if item["id"] == referee["id"])
    assert listed["aka"] == "Central"
    assert listed["display_name"] == "Central"
    assert listed["name"] == "Legal Referee Name"


def test_referee_directory_includes_secondary_referee_role():
    """The referee roster includes active users with referee among their roles."""
    app.dependency_overrides.clear()
    suffix = uuid4().hex[:10]
    admin_email = f"directory-admin-{suffix}@example.test"
    player_email = f"directory-player-{suffix}@example.test"

    admin = create_user(UserCreate(
        email=admin_email,
        name="Directory Admin",
        password="supersecret",
        role="league_admin"
    ))
    registration = client.post(
        "/api/auth/register/player",
        data={
            "email": player_email,
            "password": "supersecret",
            "name": "Secondary Referee Player",
            "curp": f"SEC{suffix.upper()}00000"[:18],
            "age": "28"
        },
        files={"photo": ("profile.png", PROFILE_PNG, "image/png")}
    )
    assert registration.status_code == 201
    player = registration.json()

    assert login(admin_email).status_code == 200
    role_update = client.put(
        f"/api/admin/users/{player['id']}/roles",
        json={"roles": ["player", "referee"]}
    )
    assert role_update.status_code == 200
    assert role_update.json()["role"] == "player"

    roster = client.get("/api/referees")
    assert roster.status_code == 200
    roster_ids = {item["id"] for item in roster.json()}
    assert player["id"] in roster_ids
    assert admin["id"] not in roster_ids
