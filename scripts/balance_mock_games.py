"""Complete mock division schedules so every team has the same game count."""

from collections import defaultdict

from database import get_connection


def _mock_score(home_team_id, away_team_id):
    """Build a deterministic non-tied score for reproducible development data."""
    home_score = 6 * (1 + ((home_team_id + away_team_id) % 7))
    away_score = 6 * ((home_team_id * 3 + away_team_id) % 7)
    if home_score == away_score:
        away_score += 1
    return home_score, away_score


def balance_mock_games():
    """Insert only the mock games needed to equalize each active division."""
    connection = get_connection()
    inserted = 0

    try:
        teams = connection.execute(
            """
            SELECT
                teams.id,
                teams.branch,
                teams.category,
                COUNT(games.id) FILTER (
                    WHERE games.home_score IS NOT NULL
                      AND games.away_score IS NOT NULL
                ) AS games_played
            FROM teams
            LEFT JOIN games
                ON games.home_team_id = teams.id
                OR games.away_team_id = teams.id
            GROUP BY teams.id, teams.branch, teams.category
            ORDER BY teams.branch, teams.category, teams.id
            """
        ).fetchall()
        next_week = connection.execute(
            "SELECT COALESCE(MAX(week), 0) + 1 AS week FROM games"
        ).fetchone()["week"]

        divisions = defaultdict(list)
        for team in teams:
            divisions[(team["branch"], team["category"])].append(dict(team))

        for division_teams in divisions.values():
            if len(division_teams) < 2:
                continue

            target = max(team["games_played"] for team in division_teams)
            if target == 0:
                continue

            deficits = {
                team["id"]: target - team["games_played"]
                for team in division_teams
            }

            # Raising the target handles any degree sequence that cannot be
            # paired at the current maximum without assigning a self-match.
            while sum(deficits.values()) % 2 or (
                deficits and max(deficits.values()) > sum(deficits.values()) / 2
            ):
                target += 1
                deficits = {
                    team["id"]: target - team["games_played"]
                    for team in division_teams
                }

            while sum(deficits.values()) > 0:
                pending = sorted(
                    (item for item in deficits.items() if item[1] > 0),
                    key=lambda item: (-item[1], item[0])
                )
                home_team_id = pending[0][0]
                away_team_id = pending[1][0]
                home_score, away_score = _mock_score(
                    home_team_id,
                    away_team_id
                )
                connection.execute(
                    """
                    INSERT INTO games (
                        home_team_id, away_team_id, home_score, away_score, week
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        home_team_id,
                        away_team_id,
                        home_score,
                        away_score,
                        next_week
                    )
                )
                deficits[home_team_id] -= 1
                deficits[away_team_id] -= 1
                inserted += 1

        connection.commit()
        return inserted
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    created = balance_mock_games()
    print(f"Mock games created: {created}")
