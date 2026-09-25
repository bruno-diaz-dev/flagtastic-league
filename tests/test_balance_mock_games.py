"""Tests for development schedule balancing."""

from database import get_connection
from scripts.balance_mock_games import balance_mock_games


def test_balance_mock_games_equalizes_a_division_and_is_idempotent():
    connection = get_connection()
    connection.execute("DELETE FROM teams")
    teams = []
    for name in ("Alpha", "Bravo", "Charlie"):
        teams.append(connection.execute(
            """
            INSERT INTO teams (name, branch, category)
            VALUES (%s, 'mixto', 'libre')
            RETURNING id
            """,
            (name,)
        ).fetchone()["id"])
    connection.execute(
        """
        INSERT INTO games (
            home_team_id, away_team_id, home_score, away_score, week
        )
        VALUES (%s, %s, 24, 18, 1), (%s, %s, 30, 12, 2)
        """,
        (teams[0], teams[1], teams[0], teams[2])
    )
    connection.commit()
    connection.close()

    assert balance_mock_games() == 1
    assert balance_mock_games() == 0

    connection = get_connection()
    counts = connection.execute(
        """
        SELECT teams.id, COUNT(games.id) AS games_played
        FROM teams
        JOIN games
            ON games.home_team_id = teams.id
            OR games.away_team_id = teams.id
        GROUP BY teams.id
        ORDER BY teams.id
        """
    ).fetchall()
    ties = connection.execute(
        "SELECT COUNT(*) AS total FROM games WHERE home_score = away_score"
    ).fetchone()["total"]
    connection.close()

    assert [row["games_played"] for row in counts] == [2, 2, 2]
    assert ties == 0
