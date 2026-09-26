"""Read model for representatives monitoring their assigned teams."""

from database import get_connection
from repositories.standings import get_standings


def get_representative_dashboard(user_id):
    """Return standings, season totals, and player totals for managed teams."""
    connection = get_connection()
    teams = connection.execute(
        """
        SELECT teams.id, teams.name, teams.branch, teams.category,
               teams.head_coach, teams.coach, teams.manager,
               teams.logo_data IS NOT NULL AS has_logo,
               COUNT(DISTINCT team_players.player_id)::INTEGER AS roster_count
        FROM team_representatives
        JOIN teams ON teams.id = team_representatives.team_id
        LEFT JOIN team_players ON team_players.team_id = teams.id
        WHERE team_representatives.user_id = %s
        GROUP BY teams.id
        ORDER BY teams.branch, teams.category, teams.name
        """,
        (user_id,)
    ).fetchall()

    team_ids = [team["id"] for team in teams]
    if not team_ids:
        connection.close()
        return {"teams": []}

    player_rows = connection.execute(
        """
        SELECT teams.id AS team_id, players.id AS player_id,
               players.name AS player_name, players.aka AS player_aka,
               team_players.jersey_number,
               COALESCE(SUM(stats.points), 0)::INTEGER AS points,
               COALESCE(SUM(stats.receptions), 0)::INTEGER AS receptions,
               COALESCE(SUM(stats.interceptions), 0)::INTEGER AS interceptions,
               COALESCE(SUM(stats.sacks), 0)::INTEGER AS sacks,
               COALESCE(SUM(stats.tackles), 0)::INTEGER AS tackles,
               COALESCE(SUM(stats.passes_completed), 0)::INTEGER AS passes_completed,
               COALESCE(SUM(stats.passes_attempted), 0)::INTEGER AS passes_attempted
        FROM teams
        JOIN team_players ON team_players.team_id = teams.id
        JOIN players ON players.id = team_players.player_id
        LEFT JOIN player_week_stats AS stats
          ON stats.team_id = teams.id AND stats.player_id = players.id
        WHERE teams.id = ANY(%s)
        GROUP BY teams.id, players.id, team_players.jersey_number
        ORDER BY teams.id, points DESC, players.name
        """,
        (team_ids,)
    ).fetchall()
    connection.close()

    players_by_team = {team_id: [] for team_id in team_ids}
    for raw_player in player_rows:
        player = dict(raw_player)
        player["completion_percentage"] = (
            round(player["passes_completed"] * 100 / player["passes_attempted"], 2)
            if player["passes_attempted"] else None
        )
        players_by_team[player.pop("team_id")].append(player)

    result = []
    for raw_team in teams:
        team = dict(raw_team)
        team["logo_url"] = (
            f"/api/teams/{team['id']}/logo" if team.pop("has_logo") else None
        )
        standings = get_standings(team["branch"], team["category"])
        standing = next(
            (row for row in standings if row["team_id"] == team["id"]),
            None
        )
        team["standing"] = {
            **(standing or {
                "wins": 0, "losses": 0, "points_for": 0,
                "points_against": 0, "point_difference": 0
            }),
            "position": next(
                (index for index, row in enumerate(standings, 1)
                 if row["team_id"] == team["id"]),
                None
            ),
            "division_team_count": len(standings)
        }
        team["players"] = players_by_team[team["id"]]
        team["statistics"] = _sum_player_statistics(team["players"])
        result.append(team)
    return {"teams": result}


def _sum_player_statistics(players):
    """Aggregate roster rows without issuing another database query."""
    metric_names = (
        "points", "receptions", "interceptions", "sacks", "tackles",
        "passes_completed", "passes_attempted"
    )
    totals = {metric: sum(player[metric] for player in players)
              for metric in metric_names}
    totals["completion_percentage"] = (
        round(totals["passes_completed"] * 100 / totals["passes_attempted"], 2)
        if totals["passes_attempted"] else None
    )
    return totals
