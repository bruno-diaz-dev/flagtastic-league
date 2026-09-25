"""Seed teams and mock roster entries referenced by an official workbook."""

import argparse
import hashlib
from pathlib import Path

from database import get_connection
from repositories.statistics import import_statistics_workbook
from services.statistics_import import parse_games_workbook, parse_statistics_workbook


def _mock_curp(branch, category, team, jersey_number):
    """Build a stable 18-character identifier so reruns remain idempotent."""
    identity = f"{branch}|{category}|{team.casefold()}|{jersey_number}"
    return f"MOCK{hashlib.sha256(identity.encode()).hexdigest()[:14]}".upper()


def seed_workbook(path):
    """Create workbook rosters, weekly statistics and inferred games."""
    content = Path(path).read_bytes()
    weeks = parse_statistics_workbook(content)
    games = parse_games_workbook(content)
    roster_entries = {
        (row["branch"], row["category"], row["team"], row["jersey_number"])
        for rows in weeks.values()
        for row in rows
    }
    team_entries = {
        (branch, category, team_name)
        for branch, category, team_name, _number in roster_entries
    }
    for week_games in games.values():
        for game in week_games:
            team_entries.add((
                game["branch"], game["category"], game["home_team"]
            ))
            team_entries.add((
                game["branch"], game["category"], game["away_team"]
            ))

    connection = get_connection()
    teams_created = 0
    players_created = 0
    existing_memberships = 0
    try:
        team_ids = {}
        for branch, category, team_name in sorted(team_entries):
            identity = (branch, category, team_name.casefold())
            if identity in team_ids:
                continue
            team = connection.execute(
                """
                SELECT id FROM teams
                WHERE LOWER(name) = LOWER(%s)
                  AND branch = %s AND category = %s
                """,
                (team_name, branch, category)
            ).fetchone()
            if team is None:
                team = connection.execute(
                    """
                    INSERT INTO teams (name, branch, category, status)
                    VALUES (%s, %s, %s, 'pending')
                    RETURNING id
                    """,
                    (team_name, branch, category)
                ).fetchone()
                teams_created += 1
            team_ids[identity] = team["id"]

        for branch, category, team_name, number in sorted(roster_entries):
            team_id = team_ids[(branch, category, team_name.casefold())]
            membership = connection.execute(
                """
                SELECT player_id FROM team_players
                WHERE team_id = %s AND jersey_number = %s
                """,
                (team_id, number)
            ).fetchone()
            if membership is not None:
                existing_memberships += 1
                continue

            curp = _mock_curp(branch, category, team_name, number)
            player = connection.execute(
                "SELECT id FROM players WHERE curp = %s",
                (curp,)
            ).fetchone()
            if player is None:
                player = connection.execute(
                    """
                    INSERT INTO players (name, curp, age)
                    VALUES (%s, %s, 18)
                    RETURNING id
                    """,
                    (f"Jugador Mock #{number} - {team_name}", curp)
                ).fetchone()
                players_created += 1
            connection.execute(
                """
                INSERT INTO team_players (team_id, player_id, jersey_number)
                VALUES (%s, %s, %s)
                """,
                (team_id, player["id"], number)
            )

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    imported = import_statistics_workbook(weeks, games)

    return {
        "weeks": len(weeks),
        "roster_entries": len(roster_entries),
        "teams_created": teams_created,
        "players_created": players_created,
        "existing_memberships": existing_memberships,
        "statistics_imported": len(imported),
        "games_imported": sum(len(rows) for rows in games.values())
    }


def main():
    parser = argparse.ArgumentParser(
        description="Create mock rosters from the official statistics workbook"
    )
    parser.add_argument("workbook", help="Path to the official .xlsx workbook")
    arguments = parser.parse_args()
    result = seed_workbook(arguments.workbook)
    print(
        "Semilla completada: "
        f"{result['weeks']} jornadas, "
        f"{result['roster_entries']} registros de roster, "
        f"{result['teams_created']} equipos nuevos y "
        f"{result['players_created']} jugadores mock nuevos; "
        f"{result['statistics_imported']} estadisticas y "
        f"{result['games_imported']} partidos cargados."
    )


if __name__ == "__main__":
    main()
