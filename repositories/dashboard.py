"""Read model for the authenticated player's personal dashboard."""

from database import get_connection
from repositories.standings import get_standings
from repositories.statistics import get_player_statistics_by_team


def update_player_aka(player_id, aka):
    """Update the player's public name without changing legal identity."""
    connection = get_connection()
    row = connection.execute(
        """
        UPDATE players SET aka = %s WHERE id = %s
        RETURNING id, name, aka
        """,
        (aka, player_id)
    ).fetchone()
    connection.commit()
    connection.close()
    return dict(row) if row is not None else None


def get_player_dashboard(player_id, team_id=None):
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
            team_players.jersey_number, team_players.active
        FROM team_players
        JOIN teams ON teams.id = team_players.team_id
        WHERE team_players.player_id = %s
          AND (team_players.active OR EXISTS (
              SELECT 1 FROM player_week_stats stats
              WHERE stats.player_id = team_players.player_id
                AND stats.team_id = team_players.team_id
          ))
        ORDER BY team_players.active DESC, teams.branch, teams.category, teams.name, teams.id
        """,
        (player_id,)
    ).fetchall()
    connection.close()

    if player is None:
        return None

    scopes = get_player_statistics_by_team(player_id)
    scoped = {row["team_id"]: row for row in scopes}
    if team_id is not None and team_id not in {row["team_id"] for row in memberships}:
        return None
    selected_team_id = team_id if team_id is not None else (memberships[0]["team_id"] if memberships else None)
    teams = []
    for membership in memberships:
        team = dict(membership)
        team["statistics"] = scoped[team["team_id"]]
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
        "selected_team_id": selected_team_id,
        "statistics": scoped.get(selected_team_id, scopes[0])
    }
