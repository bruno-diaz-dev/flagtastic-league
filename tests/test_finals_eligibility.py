"""Finals eligibility counts only played regular-season games."""

from uuid import uuid4

from fastapi.testclient import TestClient

from database import get_connection
from main import app
from repositories.finals_eligibility import get_players_below_finals_attendance


client = TestClient(app)


def create_team(name):
    response = client.post(
        "/api/teams", json={"name": name, "branch": "varonil", "category": "libre"}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_player(team_id, number):
    response = client.post(f"/api/teams/{team_id}/players", json={
        "name": f"Eligibility Player {number}", "curp": uuid4().hex[:18].upper(),
        "age": 25, "jersey_number": number,
    })
    assert response.status_code == 201, response.text
    return response.json()["id"]


def insert_game(connection, home, away, week, status="completed"):
    scores = (12, 6) if status == "completed" else (None, None)
    return connection.execute(
        """INSERT INTO games (home_team_id, away_team_id, week, status,
           home_score, away_score) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
        (home, away, week, status, *scores),
    ).fetchone()["id"]


def check_in(connection, game_id, team_id, player_id):
    connection.execute(
        "INSERT INTO game_live_sessions (game_id, state) VALUES (%s, 'completed') "
        "ON CONFLICT (game_id) DO NOTHING",
        (game_id,),
    )
    connection.execute(
        """INSERT INTO game_live_events (game_id, client_id, kind, team_id,
           player_id, player_label, period, minute, second, note)
           VALUES (%s, %s, 'attendance', %s, %s, 'Jugador', 1, 0, 0, 'Prueba')""",
        (game_id, str(uuid4()), team_id, player_id),
    )


def test_semifinals_finals_and_postponed_games_are_not_regular_season():
    suffix = uuid4().hex[:8]
    home = create_team(f"Eligibility Home {suffix}")
    away = create_team(f"Eligibility Away {suffix}")
    short = create_player(home, 1)
    regular_attendee = create_player(home, 2)
    with get_connection() as connection:
        # Other suites may leave bracket slots behind; this test defines the
        # playoff week itself.
        connection.execute("DELETE FROM game_bracket_slots")
        regular = [insert_game(connection, home, away, week) for week in range(1, 7)]
        # Postponed on week 2; the rescheduled game is one of the six above.
        insert_game(connection, home, away, 2, status="postponed")
        # Week 7: a semifinal feeding a bracket slot and a direct final that
        # has no slot of its own. Neither is regular season.
        semifinal = insert_game(connection, home, away, 7)
        insert_game(connection, home, away, 7, status="scheduled")
        connection.execute(
            """INSERT INTO game_bracket_slots (week, field_number, start_time,
               category, placement, label, source_game_id, opponent_game_id)
               VALUES (7, 9, '18:00', 'libre', 'final', 'Final Var Libre', %s, %s)""",
            (semifinal, semifinal),
        )
        # 3 regular check-ins + the semifinal: still short of 4 of 6.
        for game_id in (*regular[:3], semifinal):
            check_in(connection, game_id, home, short)
        for game_id in regular[:4]:
            check_in(connection, game_id, home, regular_attendee)

    report = {
        row["player_id"]: row for row in get_players_below_finals_attendance()
        if row["team_id"] == home
    }
    assert report[short]["scheduled_games"] == 6
    assert report[short]["attended_games"] == 3
    assert report[short]["required_games"] == 4
    # Four of six regular games meets "half plus one".
    assert regular_attendee not in report
