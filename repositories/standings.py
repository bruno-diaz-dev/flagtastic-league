"""Read model for division standings calculated from completed games."""

from database import get_connection
from services.divisions import category_allows_cross_branch_games


def get_standings(branch, category):
    """Calculate standings, combining all branches for U8 through U12."""
    connection = get_connection()

    unified = category_allows_cross_branch_games(category)
    branch_filter = "" if unified else "teams.branch = %s AND"
    parameters = (category,) if unified else (branch, category)

    rows = connection.execute(
        f"""
        SELECT
            teams.id AS team_id,
            teams.name AS team_name,
            teams.logo_data IS NOT NULL AS team_has_logo,
            COUNT(games.id) AS games_played,
            COALESCE(SUM(
                CASE
                    WHEN games.home_team_id = teams.id
                        AND games.home_score > games.away_score
                    THEN 1
                    WHEN games.away_team_id = teams.id
                        AND games.away_score > games.home_score
                    THEN 1
                    ELSE 0
                END
            ), 0) AS wins,
            COALESCE(SUM(
                CASE
                    WHEN games.home_team_id = teams.id
                        AND games.home_score < games.away_score
                    THEN 1
                    WHEN games.away_team_id = teams.id
                        AND games.away_score < games.home_score
                    THEN 1
                    ELSE 0
                END
            ), 0) AS losses,
            COALESCE(SUM(
                CASE
                    WHEN games.home_team_id = teams.id
                    THEN games.home_score
                    WHEN games.away_team_id = teams.id
                    THEN games.away_score
                    ELSE 0
                END
            ), 0) AS points_for,
            COALESCE(SUM(
                CASE
                    WHEN games.home_team_id = teams.id
                    THEN games.away_score
                    WHEN games.away_team_id = teams.id
                    THEN games.home_score
                    ELSE 0
                END
            ),0) AS points_against
        FROM teams
        LEFT JOIN games
            ON (
                games.home_team_id = teams.id
                OR games.away_team_id = teams.id
            )
            AND games.home_score IS NOT NULL
            AND games.away_score IS NOT NULL
            AND games.status = 'completed'
        WHERE
            {branch_filter}
            teams.category = %s
        GROUP BY
            teams.id,
            teams.name,
            teams.logo_data
        ORDER BY
            CASE WHEN COUNT(games.id) = 0 THEN 1 ELSE 0 END ASC,
            wins DESC,
            losses ASC,
            points_for DESC,
            teams.name ASC
        """,
        parameters
    ).fetchall()

    connection.close()

    standings = [dict(row) for row in rows]

    # Point difference is derived after aggregation to keep the SQL readable.
    for team in standings:
        # The league has no draws: played games are wins plus losses.
        team["games_played"] = team["wins"] + team["losses"]
        if team.pop("team_has_logo"):
            team["team_logo_url"] = f"/api/teams/{team['team_id']}/logo"
        team["point_difference"] = (
            team["points_for"]
            - team["points_against"]
        )

    # Teams that have played at least one completed game always rank ahead of
    # teams that have not played yet. Among active teams, preserve the league's
    # existing tiebreakers: wins, point difference, points scored, losses, name.
    standings.sort(
        key=lambda team:(
            team["games_played"] == 0,
            -team["wins"],
            -team["point_difference"],
            -team["points_for"],
            team["losses"],
            team["team_name"]
        )
    )

    return standings
