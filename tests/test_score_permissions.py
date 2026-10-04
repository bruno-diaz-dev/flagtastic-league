"""Final-score permissions, overwrite protection, and concurrent capture."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from database import get_connection
from main import app
from models import GameScoreUpdate, UserCreate
from repositories.games import GameStateConflictError, update_game_score
from repositories.users import create_user


def create_unplayed_game():
    suffix = uuid4().hex
    connection = get_connection()
    try:
        home = connection.execute(
            "INSERT INTO teams (name, branch, category) VALUES (%s, 'mixto', 'libre') RETURNING id",
            (f"score-home-{suffix}",),
        ).fetchone()["id"]
        away = connection.execute(
            "INSERT INTO teams (name, branch, category) VALUES (%s, 'mixto', 'libre') RETURNING id",
            (f"score-away-{suffix}",),
        ).fetchone()["id"]
        game_id = connection.execute(
            "INSERT INTO games (home_team_id, away_team_id, week) VALUES (%s, %s, 1) RETURNING id",
            (home, away),
        ).fetchone()["id"]
        connection.commit()
        return game_id
    finally:
        connection.close()


def authenticated_client(role):
    app.dependency_overrides.clear()
    email = f"score-{uuid4().hex}@example.test"
    create_user(UserCreate(email=email, name="Score official", password="supersecret", role=role))
    client = TestClient(app, base_url="https://testserver")
    assert client.post("/api/auth/login", json={"email": email, "password": "supersecret"}).status_code == 200
    return client


def test_referee_can_capture_once_and_only_admin_can_correct():
    game_id = create_unplayed_game()
    referee = authenticated_client("referee")
    endpoint = f"/api/games/{game_id}/score"
    first = referee.patch(endpoint, json={"home_score": 21, "away_score": 7})
    assert first.status_code == 200
    # The restriction holds for repeated requests, even the identical score.
    repeated = referee.patch(endpoint, json={"home_score": 21, "away_score": 7})
    assert repeated.status_code == 409
    assert "Solo un administrador" in repeated.json()["detail"]
    assert referee.patch(endpoint, json={"home_score": 28, "away_score": 7}).status_code == 409
    other = authenticated_client("referee")
    assert other.patch(endpoint, json={"home_score": 28, "away_score": 7}).status_code == 409
    admin = authenticated_client("league_admin")
    corrected = admin.patch(endpoint, json={"home_score": 28, "away_score": 14})
    assert corrected.status_code == 200
    assert corrected.json()["home_score"] == 28
    assert corrected.json()["away_score"] == 14
    final = next(game for game in referee.get("/api/games").json() if game["id"] == game_id)
    assert (final["home_score"], final["away_score"], final["status"]) == (28, 14, "completed")


@pytest.mark.parametrize("role", ["player", "team_representative"])
def test_other_roles_cannot_record_scores(role):
    client = authenticated_client(role)
    assert client.patch(f"/api/games/{create_unplayed_game()}/score", json={"home_score": 7, "away_score": 0}).status_code == 403


def test_anonymous_cannot_record_scores():
    app.dependency_overrides.clear()
    with TestClient(app, base_url="https://testserver") as client:
        assert client.patch("/api/games/99999/score", json={"home_score": 7, "away_score": 0}).status_code == 401


def test_referee_cannot_score_postponed_game_or_tie():
    game_id = create_unplayed_game()
    referee = authenticated_client("referee")
    endpoint = f"/api/games/{game_id}/score"
    assert referee.patch(endpoint, json={"home_score": 7, "away_score": 7}).status_code == 409
    assert referee.patch(endpoint, json={"home_score": -1, "away_score": 0}).status_code == 422
    assert referee.patch("/api/games/99999999/score", json={"home_score": 7, "away_score": 0}).status_code == 404
    connection = get_connection()
    connection.execute("UPDATE games SET status = 'postponed' WHERE id = %s", (game_id,))
    connection.commit()
    connection.close()
    assert referee.patch(endpoint, json={"home_score": 7, "away_score": 0}).status_code == 409


def test_concurrent_referee_captures_accept_exactly_one_result():
    game_id = create_unplayed_game()
    barrier = Barrier(2)

    def capture(home_score):
        barrier.wait(timeout=10)
        try:
            return update_game_score(game_id, GameScoreUpdate(home_score=home_score, away_score=7), allow_overwrite=False)
        except GameStateConflictError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(capture, [21, 28]))
    successful = [result for result in results if result is not None]
    assert len(successful) == 1
    connection = get_connection()
    stored = connection.execute("SELECT home_score, away_score FROM games WHERE id = %s", (game_id,)).fetchone()
    connection.close()
    assert stored["home_score"] == successful[0]["home_score"]
    assert stored["away_score"] == 7
