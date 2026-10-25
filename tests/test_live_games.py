"""Live capture permissions, projection, retries and atomic final publication."""
import pytest
from pydantic import ValidationError

from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from database import get_connection
from main import app
from models import UserCreate
from repositories.users import create_user
from services.live_game import project_events
from repositories.live_games import append_event, finish_live_game
from routes.live_games import LiveEvent
from migrations.versions.b3d7e9210a54_grant_live_backend_access import SCHEMA as BACKEND_GRANTS


def setup_match():
    client = TestClient(app, base_url="https://testserver")
    suffix = uuid4().hex[:8]
    teams = []
    players = []
    for side in ("Home", "Away"):
        response = client.post("/api/teams", json={"name": f"Live {side} {suffix}", "branch": "varonil", "category": "libre"})
        assert response.status_code == 201
        team = response.json()["id"]
        teams.append(team)
        side_players = []
        for number in (1, 2):
            response = client.post(f"/api/teams/{team}/players", json={
                "name": f"Live Player {side} {number}", "curp": uuid4().hex[:18].upper(),
                "age": 25, "jersey_number": number,
            })
            assert response.status_code == 201
            side_players.append(response.json()["id"])
        players.append(side_players)
    response = client.post("/api/games", json={"home_team_id": teams[0], "away_team_id": teams[1], "field_number": 1})
    assert response.status_code == 201
    game_id = response.json()["id"]
    users = {}
    for role in ("referee", "league_admin", "team_representative"):
        email = f"live-{role}-{suffix}@example.test"
        create_user(UserCreate(name=role, email=email, password="supersecret", role=role))
        users[role] = email
    app.dependency_overrides.clear()
    return client, game_id, teams, players, users


def login(client, email):
    client.cookies.clear()
    assert client.post("/api/auth/login", json={"email": email, "password": "supersecret"}).status_code == 200


def event(team, player, kind="touchdown", **extra):
    return {"client_id": str(uuid4()), "kind": kind, "team_id": team, "player_id": player, "period": 1, "minute": 12, "second": 30, **extra}


def test_live_game_roles_retry_public_privacy_and_final_publication():
    client, game_id, teams, players, users = setup_match()
    path = f"/api/games/{game_id}/live"
    assert client.post(path + "/start").status_code == 401
    login(client, users["league_admin"])
    assert client.post(path + "/start").status_code == 403
    login(client, users["referee"])
    assert client.post(path + "/start").status_code == 200
    assert client.post(path + "/finish", json={"expected_version": 1}).status_code == 409
    wrong = event(teams[0], players[1][0])
    assert client.post(path + "/events", json=wrong).status_code == 422
    scoring = event(teams[0], players[0][0], "passing_touchdown", receiver_id=players[0][1])
    first = client.post(path + "/events", json=scoring)
    assert first.status_code == 201
    retry = client.post(path + "/events", json=scoring)
    assert retry.status_code == 201 and retry.json()["id"] == first.json()["id"]
    assert client.post(path + "/events", json={**scoring, "minute": 13}).status_code == 409
    extra = client.post(path + "/events", json=event(teams[0], players[0][1], "extra_one"))
    assert extra.status_code == 201
    attendance = client.post(path + "/events", json=event(teams[0], players[0][1], "attendance"))
    assert attendance.status_code == 201
    live = client.get(path).json()
    assert live["home_score"] == 7 and live["away_score"] == 0
    assert len(live["events"]) == 2
    assert "recorded_by" not in live["events"][0]
    assert "curp" not in str(live) and "birth_date" not in str(live)
    assert "started_by" not in live
    assert client.post(path + "/finish", json={"expected_version": 1}).status_code == 409
    login(client, users["team_representative"])
    assert client.post(path + "/events", json=event(teams[0], players[0][1])).status_code == 403
    assert client.post(path + "/finish", json={"expected_version": live["version"]}).status_code == 403
    login(client, users["referee"])
    assert client.patch(f"/api/games/{game_id}/score", json={"home_score": 7, "away_score": 0}).status_code == 409
    assert client.post(path + "/finish", json={"expected_version": live["version"]}).status_code == 200
    assert client.post(path + "/events", json=event(teams[0], players[0][1])).status_code == 409
    assert client.post(path + f"/events/{extra.json()['id']}/void", json={"reason": "Duplicada", "expected_version": live["version"] + 1}).status_code == 403
    login(client, users["league_admin"])
    assert client.post(path + f"/events/{extra.json()['id']}/void", json={"reason": "Duplicada", "expected_version": live["version"] + 1}).status_code == 200
    final = client.get(path).json()
    assert final["state"] == "completed" and final["home_score"] == 6
    assert extra.json()["id"] not in [row["id"] for row in final["events"]]
    assert next(row for row in final["attendance"] if row["player_id"] == players[0][1])["attended_games"] == 1
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM player_week_stats WHERE game_id = %s", (game_id,)).fetchall()
    stats = {row["player_id"]: row for row in rows}
    assert stats[players[0][0]]["passes_attempted"] == 1
    assert stats[players[0][0]]["passes_completed"] == 1
    assert stats[players[0][1]]["points"] == 6
    assert stats[players[0][1]]["receptions"] == 1
    assert len(rows) == 2
    client.cookies.clear()
    assert client.get(path).status_code == 200


def test_live_void_is_audited_and_cannot_erase_final_result_into_a_tie():
    client, game_id, teams, players, users = setup_match()
    login(client, users["referee"])
    path = f"/api/games/{game_id}/live"
    assert client.post(path + "/start").status_code == 200
    score = client.post(path + "/events", json=event(teams[0], players[0][1])).json()
    live = client.get(path).json()
    assert client.post(path + f"/events/{score['id']}/void", json={"reason": "Captura equivocada", "expected_version": live["version"]}).status_code == 200
    corrected = client.get(path).json()
    assert corrected["home_score"] == 0 and corrected["events"] == []
    assert corrected["statistics"] == []
    with get_connection() as connection:
        audit = connection.execute("SELECT voided_at, void_reason FROM game_live_events WHERE id=%s", (score["id"],)).fetchone()
    assert audit["voided_at"] is not None and audit["void_reason"] == "Captura equivocada"
    assert client.post(path + "/finish", json={"expected_version": corrected["version"]}).status_code == 409
    score = client.post(path + "/events", json=event(teams[1], players[1][1])).json()
    live = client.get(path).json()
    assert client.post(path + "/finish", json={"expected_version": live["version"]}).status_code == 200
    login(client, users["league_admin"])
    closed = client.get(path).json()
    assert client.post(path + f"/events/{score['id']}/void", json={"reason": "No debe quedar empate", "expected_version": closed["version"]}).status_code == 409
    assert client.get(path).json()["away_score"] == 6


def test_live_projection_defense_and_voided_events():
    base = {"team_id": 1, "player_id": 10, "receiver_id": None}
    events = [{**base, "kind": kind} for kind in ("sack", "flag", "interception", "attendance", "pass_incomplete")]
    events += [{**base, "kind": "touchdown", "voided_at": "2026-10-04"}, {**base, "kind": "extra_two"}]
    score, rows = project_events(events, 1, 2)
    assert score == {1: 2, 2: 0}
    assert rows[0]["sacks"] == rows[0]["tackles"] == rows[0]["interceptions"] == 1
    assert rows[0]["passes_attempted"] == 1 and rows[0]["passes_completed"] == 0
    assert "attendance" not in rows[0]


def test_concurrent_live_retries_and_finish_publish_once():
    client, game_id, teams, players, users = setup_match()
    login(client, users["referee"])
    user_id = client.get("/api/auth/me").json()["id"]
    path = f"/api/games/{game_id}/live"
    assert client.post(path + "/start").status_code == 200
    payload = LiveEvent(**event(teams[0], players[0][1])).model_dump()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: append_event(game_id, payload, user_id), range(2)))
    assert results[0]["id"] == results[1]["id"]
    assert sorted(result["duplicate"] for result in results) == [False, True]
    snapshot = client.get(path).json()
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: finish_live_game(game_id, snapshot["version"], user_id), range(2)))
    with get_connection() as connection:
        count = connection.execute("SELECT COUNT(*) AS count FROM player_week_stats WHERE game_id = %s", (game_id,)).fetchone()["count"]
    assert count == 1
    assert client.get(path).json()["home_score"] == 6


def test_restricted_backend_role_can_read_and_write_live_tables():
    """Exercise the production database role, not just the test owner."""
    client, game_id, teams, players, users = setup_match()
    connection = get_connection()
    try:
        connection.execute("""DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flagtastic_app') THEN
                CREATE ROLE flagtastic_app NOLOGIN;
            END IF;
        END $$;""")
        connection.execute(BACKEND_GRANTS)
        connection.execute("SET LOCAL ROLE flagtastic_app")
        assert connection.execute("SELECT current_user AS role").fetchone()["role"] == "flagtastic_app"
        connection.execute("INSERT INTO game_live_sessions(game_id) VALUES (%s)", (game_id,))
        saved = connection.execute("""
            INSERT INTO game_live_events(game_id,client_id,kind,team_id,period,minute,second,note)
            VALUES (%s,%s,'note',%s,1,0,0,'Permission verification') RETURNING id
        """, (game_id, uuid4(), teams[0])).fetchone()
        assert saved["id"] > 0
        assert connection.execute("SELECT state FROM game_live_sessions WHERE game_id=%s", (game_id,)).fetchone()["state"] == "live"
    finally:
        # No test role, grants, policies, session or event escapes this check.
        connection.rollback()
        connection.close()

def test_live_events_require_statistics_and_never_manual_commentary():
    payload = event(1, 10, "passing_touchdown", receiver_id=11)
    saved = LiveEvent(**payload).model_dump()
    assert saved["note"] == ""
    assert saved["player_id"] == 10 and saved["receiver_id"] == 11
    with pytest.raises(ValidationError):
        LiveEvent(**{**payload, "note": "Manual description"})
    with pytest.raises(ValidationError):
        LiveEvent(**{**payload, "kind": "note", "receiver_id": None})
    with pytest.raises(ValidationError):
        LiveEvent(**{**payload, "kind": "flag", "player_id": None, "receiver_id": None})


def test_match_moments_and_attendance_are_not_sporting_statistics():
    client, game_id, teams, players, users = setup_match()
    path = f"/api/games/{game_id}/live"
    login(client, users["referee"])
    assert client.post(path + "/start").status_code == 200
    for kind in ("halftime", "two_minute_warning"):
        payload = event(None, None, kind)
        response = client.post(path + "/events", json=payload)
        assert response.status_code == 201
        assert client.post(path + "/events", json=payload).json()["id"] == response.json()["id"]
        assert client.post(path + "/events", json=event(teams[0], players[0][0], kind)).status_code == 422
    for _ in range(2):
        assert client.post(path + "/events", json=event(teams[0], players[0][0], "attendance")).status_code == 201
    snapshot = client.get(path).json()
    assert len(snapshot["events"]) == 2
    assert snapshot["statistics"] == []
    assert snapshot["home_score"] == snapshot["away_score"] == 0
    row = next(r for r in snapshot["attendance"] if r["player_id"] == players[0][0])
    assert row["present"] and row["attended_games"] == 0 and not row["eligible"]
    assert client.post(path + "/events", json=event(teams[0], players[0][1])).status_code == 201
    snapshot = client.get(path).json()
    assert client.post(path + "/finish", json={"expected_version":snapshot["version"]}).status_code == 200
    row = next(r for r in client.get(path).json()["attendance"] if r["player_id"] == players[0][0])
    assert row["attended_games"] == 1 and row["required_games"] == 1 and row["eligible"]
    with get_connection() as connection:
        assert connection.execute("SELECT COUNT(*) AS count FROM player_week_stats WHERE game_id=%s", (game_id,)).fetchone()["count"] == 1

    closed = client.get(path).json()
    correction = {"reason":"No asistió", "expected_version":closed["version"]}
    assert client.post(path + f"/events/{row['entry_id']}/void", json=correction).status_code == 403
    login(client, users["league_admin"])
    with get_connection() as connection:
        connection.execute("UPDATE games SET home_score=99, away_score=42 WHERE id=%s", (game_id,))
    assert client.post(path + f"/events/{row['entry_id']}/void", json=correction).status_code == 200
    corrected = client.get(path).json()
    assert (corrected["home_score"], corrected["away_score"]) == (99,42)
    row = next(r for r in corrected["attendance"] if r["player_id"] == players[0][0])
    assert row["attended_games"] == 0 and not row["present"] and not row["eligible"]



@pytest.mark.parametrize("kind", ["pass_complete", "pass_incomplete", "passing_touchdown", "touchdown", "extra_one", "extra_two", "safety", "sack", "flag", "interception"])
def test_voided_play_contributes_no_score_or_player_statistics(kind):
    scores, totals = project_events([{"kind":kind, "team_id":1, "player_id":10,
                                    "receiver_id":11, "voided_at":"2026-10-05"}], 1, 2)
    assert scores == {1:0, 2:0}
    assert totals == []


def test_attendance_before_live_capture_permissions_retry_and_correction():
    client, game_id, teams, players, users = setup_match()
    path = f"/api/games/{game_id}/live"
    payload = {"client_id": str(uuid4()), "team_id": teams[0], "player_id": players[0][0]}
    assert client.post(path + "/attendance", json=payload).status_code == 401
    login(client, users["team_representative"])
    assert client.post(path + "/attendance", json=payload).status_code == 403
    login(client, users["referee"])
    first = client.post(path + "/attendance", json=payload)
    assert first.status_code == 201
    retry = client.post(path + "/attendance", json=payload)
    assert retry.json() == {"id": first.json()["id"], "duplicate": True}
    snapshot = client.get(path).json()
    assert snapshot["state"] == "not_started" and snapshot["version"] == 0
    assert snapshot["events"] == [] and snapshot["statistics"] == []
    assert snapshot["home_score"] == snapshot["away_score"] == 0
    assert next(r for r in snapshot["attendance"] if r["player_id"] == players[0][0])["present"]
    assert client.post(path + "/attendance", json={**payload, "client_id": str(uuid4()), "player_id": players[1][0]}).status_code == 422
    assert client.post(path + f"/events/{first.json()['id']}/void", json={"reason": "Captura incorrecta", "expected_version": 0}).status_code == 200
    assert not next(r for r in client.get(path).json()["attendance"] if r["player_id"] == players[0][0])["present"]
    assert client.post(path + "/attendance", json={**payload, "client_id": str(uuid4())}).status_code == 201
    assert client.post(path + "/start").status_code == 200
    assert next(r for r in client.get(path).json()["attendance"] if r["player_id"] == players[0][0])["present"]


def test_admin_attendance_after_manual_result_preserves_score_and_statistics():
    client, game_id, teams, players, users = setup_match()
    path = f"/api/games/{game_id}/live"
    login(client, users["league_admin"])
    assert client.patch(f"/api/games/{game_id}/score", json={"home_score": 19, "away_score": 6}).status_code == 200
    payload = {"client_id": str(uuid4()), "team_id": teams[0], "player_id": players[0][0]}
    first = client.post(path + "/attendance", json=payload)
    assert first.status_code == 201
    snapshot = client.get(path).json()
    assert snapshot["state"] == "completed"
    assert (snapshot["home_score"], snapshot["away_score"]) == (19, 6)
    row = next(r for r in snapshot["attendance"] if r["player_id"] == players[0][0])
    assert row["present"] and row["attended_games"] == 1
    assert snapshot["events"] == [] and snapshot["statistics"] == []
    assert client.post(path + "/events", json=event(teams[0], players[0][0])).status_code == 403
    login(client, users["referee"])
    assert client.post(path + "/attendance", json={**payload, "client_id": str(uuid4())}).status_code == 403
    correction = {"reason": "Jugador ausente", "expected_version": snapshot["version"]}
    assert client.post(path + f"/events/{first.json()['id']}/void", json=correction).status_code == 403
    login(client, users["league_admin"])
    assert client.post(path + f"/events/{first.json()['id']}/void", json=correction).status_code == 200
    snapshot = client.get(path).json()
    assert (snapshot["home_score"], snapshot["away_score"]) == (19, 6)
    assert not next(r for r in snapshot["attendance"] if r["player_id"] == players[0][0])["present"]


def test_started_game_can_be_postponed_without_losing_capture_and_resumed():
    client, game_id, teams, players, users = setup_match()
    path = f"/api/games/{game_id}/live"
    login(client, users["referee"])
    assert client.post(path + "/start").status_code == 200
    play = event(teams[0], players[0][0])
    assert client.post(path + "/events", json=play).status_code == 201
    before = client.get(path).json()
    login(client, users["league_admin"])
    assert client.patch(f"/api/games/{game_id}/status", json={"status": "postponed"}).status_code == 200
    suspended = client.get(path).json()
    assert suspended["state"] == "postponed"
    assert suspended["home_score"] == before["home_score"]
    assert suspended["version"] == before["version"] + 1
    login(client, users["referee"])
    assert client.post(path + "/events", json=event(teams[1], players[1][0])).status_code == 409
    assert client.post(path + "/finish", json={"expected_version": suspended["version"]}).status_code == 409
    login(client, users["league_admin"])
    assert client.patch(f"/api/games/{game_id}/status", json={"status": "scheduled"}).status_code == 200
    resumed = client.get(path).json()
    assert resumed["state"] == "live"
    assert resumed["version"] == before["version"] + 2
    assert resumed["home_score"] == before["home_score"]
    login(client, users["referee"])
    assert client.post(path + "/finish", json={"expected_version": before["version"]}).status_code == 409
    assert client.post(path + "/events", json=event(teams[1], players[1][0])).status_code == 201


def test_week_postponement_includes_started_games():
    client, game_id, teams, players, users = setup_match()
    path = f"/api/games/{game_id}/live"
    with get_connection() as connection:
        connection.execute("UPDATE games SET week = 9876 WHERE id = %s", (game_id,))
    login(client, users["referee"])
    assert client.post(path + "/start").status_code == 200
    login(client, users["league_admin"])
    response = client.patch('/api/games/week/9876/status', json={"status": "postponed"})
    assert response.status_code == 200
    assert response.json()["updated"] == 1
    assert client.get(path).json()["state"] == "postponed"


def test_passing_touchdown_never_credits_qb_personal_points_without_receiver():
    _, rows = project_events([{'kind': 'passing_touchdown', 'team_id': 1, 'player_id': 5, 'receiver_id': None}], 1, 2)
    assert rows[0]['points'] == 0
    assert rows[0]['passing_points'] == 6


@pytest.mark.parametrize('final_score', [(0, 0), (12, 12), (26, 18)])
@pytest.mark.parametrize('finisher', ['league_admin', 'referee'])
def test_empty_roster_friendly_can_close_with_real_score_without_season_statistics(final_score, finisher):
    client, _, _, _, users = setup_match()
    login(client, users['league_admin'])
    response = client.post('/api/games', json={
        'is_friendly': True, 'home_guest_name': 'Sele U17', 'away_guest_name': 'Sele U15',
        'branch': 'varonil', 'category': 'u18', 'week': 4, 'field_number': 2,
    })
    assert response.status_code == 201
    game_id = response.json()['id']
    path = f'/api/games/{game_id}/live'
    login(client, users['referee'])
    assert client.post(path + '/start').status_code == 200
    snapshot = client.get(path).json()
    assert snapshot['roster'] == [] and snapshot['events'] == []
    payload = {'expected_version': snapshot['version'], 'home_score': final_score[0], 'away_score': final_score[1]}
    client.cookies.clear()
    assert client.post(path + '/finish', json=payload).status_code == 401
    login(client, users['team_representative'])
    assert client.post(path + '/finish', json=payload).status_code == 403
    login(client, users[finisher])
    assert client.post(path + '/finish', json={**payload, 'expected_version': 0}).status_code == 409
    assert client.post(path + '/finish', json=payload).status_code == 200
    assert client.post(path + '/finish', json=payload).status_code == 200
    assert client.post(path + '/finish', json={**payload, 'home_score': final_score[0] + 1}).status_code == 409
    closed = client.get(path).json()
    assert closed['state'] == 'completed'
    assert (closed['home_score'], closed['away_score']) == final_score
    assert closed['events'] == [] and closed['statistics'] == [] and closed['finished_at']
    with get_connection() as connection:
        assert connection.execute('SELECT COUNT(*) AS n FROM player_week_stats WHERE game_id=%s', (game_id,)).fetchone()['n'] == 0
        session = connection.execute('SELECT finished_by, version FROM game_live_sessions WHERE game_id=%s', (game_id,)).fetchone()
        user = connection.execute('SELECT id FROM users WHERE email=%s', (users[finisher],)).fetchone()
        assert session['finished_by'] == user['id'] and session['version'] == snapshot['version'] + 1


def test_friendly_scoring_capture_cannot_be_overridden_and_tied_capture_can_finish():
    client, game_id, teams, players, users = setup_match()
    with get_connection() as connection:
        connection.execute('UPDATE games SET is_friendly=true WHERE id=%s', (game_id,))
    login(client, users['referee'])
    path = f'/api/games/{game_id}/live'
    assert client.post(path + '/start').status_code == 200
    for team, roster in zip(teams, players):
        assert client.post(path + '/events', json=event(team, roster[0])).status_code == 201
    snapshot = client.get(path).json()
    assert snapshot['home_score'] == snapshot['away_score'] == 6
    overridden = client.post(path + '/finish', json={'expected_version': snapshot['version'], 'home_score': 99, 'away_score': 0})
    assert overridden.status_code == 409
    assert client.get(path).json()['state'] == 'live'
    assert client.post(path + '/finish', json={'expected_version': snapshot['version']}).status_code == 200
    with get_connection() as connection:
        assert connection.execute('SELECT COUNT(*) AS n FROM player_week_stats WHERE game_id=%s', (game_id,)).fetchone()['n'] == 0


def test_official_game_cannot_bypass_capture_with_a_direct_final_score():
    client, game_id, teams, players, users = setup_match()
    login(client, users['referee'])
    path = f'/api/games/{game_id}/live'
    assert client.post(path + '/start').status_code == 200
    snapshot = client.get(path).json()
    assert client.post(path + '/finish', json={'expected_version': snapshot['version'], 'home_score': 6, 'away_score': 0}).status_code == 422
    assert client.post(path + '/finish', json={'expected_version': snapshot['version']}).status_code == 409
    assert client.get(path).json()['state'] == 'live'


def test_friendly_final_score_is_kept_when_a_pause_is_corrected_after_closing():
    client, game_id, _, _, users = setup_match()
    with get_connection() as connection:
        connection.execute('UPDATE games SET is_friendly=true WHERE id=%s', (game_id,))
    login(client, users['referee'])
    path = f'/api/games/{game_id}/live'
    assert client.post(path + '/start').status_code == 200
    pause = client.post(path + '/events', json={
        'client_id': str(uuid4()), 'kind': 'halftime', 'period': 1, 'minute': 20, 'second': 0,
    }).json()
    snapshot = client.get(path).json()
    login(client, users['league_admin'])
    assert client.post(path + '/finish', json={'expected_version': snapshot['version'], 'home_score': 18, 'away_score': 12}).status_code == 200
    closed = client.get(path).json()
    assert client.post(path + f"/events/{pause['id']}/void", json={'expected_version': closed['version'], 'reason': 'Pausa equivocada'}).status_code == 200
    corrected = client.get(path).json()
    assert (corrected['home_score'], corrected['away_score']) == (18, 12)


@pytest.mark.parametrize('scores', [{'home_score': 6}, {'away_score': 0}, {'home_score': -1, 'away_score': 0}, {'home_score': 1.5, 'away_score': 0}, {'home_score': 2_147_483_648, 'away_score': 0}])
def test_live_finish_requires_both_nonnegative_integer_scores(scores):
    from routes.live_games import LiveFinish
    with pytest.raises(ValidationError):
        LiveFinish(expected_version=1, **scores)


def test_cancel_accidental_capture_preserves_attendance_audit_and_restart_safety():
    import json
    client, game_id, teams, players, users = setup_match()
    path = f'/api/games/{game_id}/live'
    login(client, users['referee'])
    starter_id = client.get('/api/auth/me').json()['id']
    assert client.post(path + '/start').status_code == 200
    original_start = client.get(path).json()['started_at']
    attendance = client.post(path + '/events', json=event(teams[0], players[0][0], 'attendance')).json()
    pause = client.post(path + '/events', json={'client_id': str(uuid4()), 'kind': 'halftime', 'period': 1, 'minute': 20, 'second': 0}).json()
    original = client.get(path).json()
    payload = {'expected_version': original['version']}
    for role in ['referee', 'team_representative']:
        login(client, users[role])
        assert client.post(path + '/cancel', json=payload).status_code == 403
    client.cookies.clear()
    assert client.post(path + '/cancel', json=payload).status_code == 401
    login(client, users['league_admin'])
    admin_id = client.get('/api/auth/me').json()['id']
    # A stale confirmation cannot cancel a newly changed capture.
    assert client.post(path + '/cancel', json={'expected_version': 1}).status_code == 409
    with get_connection() as connection:
        game_before = dict(connection.execute('SELECT * FROM games WHERE id=%s', (game_id,)).fetchone())
    assert client.post(path + '/cancel', json=payload).status_code == 200
    assert client.post(path + '/cancel', json=payload).status_code == 200
    pending = client.get(path).json()
    assert pending['state'] == 'not_started' and pending['version'] > original['version']
    assert pending['started_at'] is None and pending['finished_at'] is None
    assert pending['events'] == [] and pending['statistics'] == []
    assert next(row for row in pending['attendance'] if row['player_id'] == players[0][0])['present']
    with get_connection() as connection:
        game_after = dict(connection.execute('SELECT * FROM games WHERE id=%s', (game_id,)).fetchone())
        assert game_after == game_before
        rows = connection.execute('SELECT * FROM game_live_events WHERE game_id=%s ORDER BY id', (game_id,)).fetchall()
        audit = [row for row in rows if row['kind'] == 'note']
        assert len(audit) == 1
        metadata = json.loads(audit[0]['note'])
        assert metadata['started_by'] == starter_id and metadata['started_at'] == original_start
        assert metadata['version'] == pending['version']
        assert audit[0]['recorded_by'] == admin_id and audit[0]['voided_by'] == admin_id
        assert audit[0]['void_reason'] == 'Captura iniciada por error' and audit[0]['voided_at']
        assert next(row for row in rows if row['id'] == pause['id'])['voided_at']
        assert next(row for row in rows if row['id'] == attendance['id'])['voided_at'] is None
        assert connection.execute('SELECT 1 FROM game_live_sessions WHERE game_id=%s', (game_id,)).fetchone() is None
    # Independent attendance correction still works while the fixture is pending.
    assert client.post(path + f"/events/{attendance['id']}/void", json={'expected_version': pending['version'], 'reason': 'Asistencia equivocada'}).status_code == 200
    login(client, users['referee'])
    assert client.post(path + '/start').status_code == 200
    restarted = client.get(path).json()
    assert restarted['state'] == 'live' and restarted['version'] > pending['version']
    assert restarted['started_at'] != original_start
    old_play = event(teams[0], players[0][0], 'pass_incomplete', capture_started_at=original_start)
    assert client.post(path + '/events', json=old_play).status_code == 409
    # Cached older clients must refresh after a cancelled capture.
    assert client.post(path + '/events', json=event(teams[0], players[0][0], 'pass_incomplete')).status_code == 409
    new_play = event(teams[0], players[0][0], 'pass_incomplete', capture_started_at=restarted['started_at'])
    assert client.post(path + '/events', json=new_play).status_code == 201
    login(client, users['league_admin'])
    assert client.post(path + '/cancel', json=payload).status_code == 409
    active = client.get(path).json()
    assert active['state'] == 'live' and len(active['events']) == 1
    assert client.post(path + '/cancel', json={'expected_version': active['version']}).status_code == 409


@pytest.mark.parametrize('kind', ['pass_incomplete', 'flag', 'touchdown'])
def test_cancel_cannot_discard_confirmed_sporting_plays_even_at_zero_zero(kind):
    client, game_id, teams, players, users = setup_match()
    path = f'/api/games/{game_id}/live'
    login(client, users['referee'])
    assert client.post(path + '/start').status_code == 200
    assert client.post(path + '/events', json=event(teams[0], players[0][0], kind)).status_code == 201
    snapshot = client.get(path).json()
    login(client, users['league_admin'])
    result = client.post(path + '/cancel', json={'expected_version': snapshot['version']})
    assert result.status_code == 409 and 'jugadas confirmadas' in result.json()['detail']
    assert client.get(path).json()['events'] == snapshot['events']
    # An administrator must explicitly void the mistaken play first.
    play_id = snapshot['events'][0]['id']
    assert client.post(path + f'/events/{play_id}/void', json={'expected_version': snapshot['version'], 'reason': 'Captura equivocada'}).status_code == 200
    reviewed = client.get(path).json()
    assert client.post(path + '/cancel', json={'expected_version': reviewed['version']}).status_code == 200


def test_cancel_preserves_previously_voided_plays_and_can_restart_repeatedly():
    client, game_id, teams, players, users = setup_match()
    path = f'/api/games/{game_id}/live'
    login(client, users['referee'])
    assert client.post(path + '/start').status_code == 200
    scoring = client.post(path + '/events', json=event(teams[0], players[0][0])).json()
    snapshot = client.get(path).json()
    assert client.post(path + f"/events/{scoring['id']}/void", json={'expected_version': snapshot['version'], 'reason': 'Captura equivocada'}).status_code == 200
    versions = [client.get(path).json()['version']]
    for _ in range(2):
        login(client, users['league_admin'])
        assert client.post(path + '/cancel', json={'expected_version': versions[-1]}).status_code == 200
        pending = client.get(path).json()
        versions.append(pending['version'])
        login(client, users['referee'])
        assert client.post(path + '/start').status_code == 200
        versions.append(client.get(path).json()['version'])
    assert versions == sorted(set(versions))
    with get_connection() as connection:
        original = connection.execute('SELECT * FROM game_live_events WHERE id=%s', (scoring['id'],)).fetchone()
        assert original['void_reason'] == 'Captura equivocada' and original['voided_at']
        assert connection.execute("SELECT COUNT(*) AS n FROM game_live_events WHERE game_id=%s AND kind='note'", (game_id,)).fetchone()['n'] == 2


@pytest.mark.parametrize('state', ['postponed', 'completed', 'with_statistics'])
def test_cancel_refuses_games_with_results_postponements_or_published_statistics(state):
    client, game_id, teams, players, users = setup_match()
    path = f'/api/games/{game_id}/live'
    login(client, users['referee'])
    assert client.post(path + '/start').status_code == 200
    with get_connection() as connection:
        if state == 'with_statistics':
            connection.execute('INSERT INTO player_week_stats (week,game_id,player_id,team_id) VALUES (1,%s,%s,%s)', (game_id, players[0][0], teams[0]))
        else:
            connection.execute('UPDATE games SET status=%s,home_score=%s,away_score=%s WHERE id=%s', (state, 6 if state == 'completed' else None, 0 if state == 'completed' else None, game_id))
    snapshot = client.get(path).json()
    login(client, users['league_admin'])
    assert client.post(path + '/cancel', json={'expected_version': snapshot['version']}).status_code == 409
    with get_connection() as connection:
        assert connection.execute('SELECT 1 FROM game_live_sessions WHERE game_id=%s', (game_id,)).fetchone()
        assert connection.execute("SELECT 1 FROM game_live_events WHERE game_id=%s AND kind='note'", (game_id,)).fetchone() is None


def test_concurrent_cancel_and_capture_never_erase_an_accepted_play():
    from repositories.live_games import cancel_live_game, LiveGameError
    from threading import Barrier
    client, game_id, teams, players, users = setup_match()
    path = f'/api/games/{game_id}/live'
    login(client, users['referee'])
    referee_id = client.get('/api/auth/me').json()['id']
    assert client.post(path + '/start').status_code == 200
    snapshot = client.get(path).json()
    login(client, users['league_admin'])
    admin_id = client.get('/api/auth/me').json()['id']
    payload = LiveEvent(**event(teams[0], players[0][0], 'pass_incomplete', capture_started_at=snapshot['started_at'])).model_dump()
    barrier = Barrier(2)
    def operation(cancel):
        barrier.wait(timeout=10)
        try:
            return cancel_live_game(game_id, snapshot['version'], admin_id) if cancel else append_event(game_id, payload, referee_id)
        except LiveGameError:
            return None
    with ThreadPoolExecutor(max_workers=2) as executor:
        cancel_result, play_result = list(executor.map(operation, [True, False]))
    assert (cancel_result is None) != (play_result is None)
    current = client.get(path).json()
    assert (current['state'], len(current['events'])) == (('not_started', 0) if cancel_result else ('live', 1))


def test_cancel_rolls_back_on_legacy_session_cascade_instead_of_losing_attendance():
    client, game_id, teams, players, users = setup_match()
    path = f'/api/games/{game_id}/live'
    login(client, users['referee'])
    assert client.post(path + '/start').status_code == 200
    assert client.post(path + '/events', json=event(teams[0], players[0][0], 'attendance')).status_code == 201
    snapshot = client.get(path).json()
    login(client, users['league_admin'])
    with get_connection() as connection:
        connection.execute('ALTER TABLE game_live_events DROP CONSTRAINT game_live_events_game_id_fkey')
        connection.execute('ALTER TABLE game_live_events ADD CONSTRAINT game_live_events_game_id_fkey FOREIGN KEY (game_id) REFERENCES game_live_sessions(game_id) ON DELETE CASCADE NOT VALID')
    try:
        result = client.post(path + '/cancel', json={'expected_version': snapshot['version']})
        assert result.status_code == 409 and 'conservar el historial' in result.json()['detail']
        current = client.get(path).json()
        assert current['state'] == 'live' and current['version'] == snapshot['version']
        assert next(row for row in current['attendance'] if row['player_id'] == players[0][0])['present']
        with get_connection() as connection:
            assert connection.execute("SELECT COUNT(*) AS n FROM game_live_events WHERE game_id=%s AND kind='note'", (game_id,)).fetchone()['n'] == 0
    finally:
        with get_connection() as connection:
            connection.execute('ALTER TABLE game_live_events DROP CONSTRAINT game_live_events_game_id_fkey')
            connection.execute('ALTER TABLE game_live_events ADD CONSTRAINT game_live_events_game_id_fkey FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE')
