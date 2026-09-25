"""Read model for the authenticated player's personal dashboard."""

from database import get_connection
from repositories.standings import get_standings
from repositories.statistics import get_player_statistics


def get_player_dashboard(player_id):
    """Combine identity, memberships, statistics and standings positions."""
    connection = get_connection()
    player = connection.execute(
        """
        SELECT id, name, age, aka,
               CASE
                   WHEN profile_photo_path IS NULL THEN NULL
                   ELSE '/media/profiles/' || profile_photo_path
               END AS profile_photo_url
        FROM players
        WHERE id = %s
        """,
        (player_id,)
    ).fetchone()
    memberships = connection.execute(
        """
        SELECT
            teams.id AS team_id,
            teams.name AS team_name,
            teams.branch,
            teams.category,
            team_players.jersey_number
        FROM team_players
        JOIN teams ON teams.id = team_players.team_id
        WHERE team_players.player_id = %s
        ORDER BY teams.branch, teams.category, teams.name
        """,
        (player_id,)
    ).fetchall()
    connection.close()

    if player is None:
        return None

    teams = []
    for membership in memberships:
        team = dict(membership)
        standings = get_standings(team["branch"], team["category"])
        team["standing_position"] = next(
            (
                index
                for index, row in enumerate(standings, start=1)
                if row["team_id"] == team["team_id"]
            ),
            None
        )
        team["division_team_count"] = len(standings)
        teams.append(team)

    return {
        "player": dict(player),
        "teams": teams,
        "statistics": get_player_statistics(player_id)
    }
