"""Semifinal results fill, correct or protect the pre-created final."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from database import get_connection
from main import app
from services.bracket_advancement import (
    BracketConflictError, resolve_completed_bracket_slots,
)


client = TestClient(app)


def create_team(name):
    response = client.post(
        "/api/teams", json={"name": name, "branch": "varonil", "category": "libre"}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def setup_bracket(connection):
    suffix = uuid4().hex[:6]
    a, b, c, d = (create_team(f"Bracket {letter} {suffix}") for letter in "ABCD")
    semis = []
    for field, (home, away) in enumerate(((a, b), (c, d)), 1):
        semis.append(connection.execute(
            """INSERT INTO games (home_team_id, away_team_id, week, field_number,
               start_time, status, home_score, away_score)
               VALUES (%s, %s, 7, %s, '10:00', 'completed', 20, 6) RETURNING id""",
            (home, away, field),
        ).fetchone()["id"])
    final = connection.execute(
        """INSERT INTO games (home_team_id, away_team_id, week, field_number,
           start_time, home_pending_label, away_pending_label)
           VALUES (NULL, NULL, 7, 1, '12:00', 'Final', 'Final') RETURNING id"""
    ).fetchone()["id"]
    connection.execute(
        """INSERT INTO game_bracket_slots (week, field_number, start_time, category,
           placement, label, source_game_id, opponent_game_id, target_game_id)
           VALUES (7, 1, '12:00', 'libre', 'final', 'Final Var Libre', %s, %s, %s)""",
        (semis[0], semis[1], final),
    )
    return (a, b, c, d), semis, final


def final_teams(connection, final):
    row = connection.execute(
        "SELECT home_team_id, away_team_id FROM games WHERE id=%s", (final,)
    ).fetchone()
    return row["home_team_id"], row["away_team_id"]


def test_corrected_semifinal_updates_a_final_that_has_not_started():
    connection = get_connection()
    try:
        connection.execute("DELETE FROM game_bracket_slots")
        (a, b, c, _d), semis, final = setup_bracket(connection)
        resolve_completed_bracket_slots(connection, semis[0])
        assert final_teams(connection, final) == (a, c)

        connection.execute(
            "UPDATE games SET home_score=6, away_score=20 WHERE id=%s", (semis[0],)
        )
        resolve_completed_bracket_slots(connection, semis[0])
        assert final_teams(connection, final) == (b, c)
    finally:
        connection.rollback()
        connection.close()


def test_corrected_semifinal_is_rejected_once_the_final_started():
    connection = get_connection()
    try:
        connection.execute("DELETE FROM game_bracket_slots")
        (a, _b, c, _d), semis, final = setup_bracket(connection)
        resolve_completed_bracket_slots(connection, semis[0])
        connection.execute(
            "INSERT INTO game_live_sessions (game_id, state) VALUES (%s, 'live')", (final,)
        )
        connection.execute(
            "UPDATE games SET home_score=6, away_score=20 WHERE id=%s", (semis[0],)
        )
        with pytest.raises(BracketConflictError):
            resolve_completed_bracket_slots(connection, semis[0])
        assert final_teams(connection, final) == (a, c)
    finally:
        connection.rollback()
        connection.close()
