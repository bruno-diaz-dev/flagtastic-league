from database import get_connection


def get_standings(branch, category):
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            teams.id AS team_id,
            teams.name AS team_name,
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
                    WHEN games.home_score = games.away_score
                    THEN 1
                    ELSE 0
                END
            ), 0) AS ties,
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
        WHERE
            teams.branch = %s
            AND teams.category = %s
        GROUP BY
            teams.id,
            teams.name
        ORDER BY
            wins DESC,
            losses ASC,
            points_for DESC,
            teams.name ASC
        """,
        (
            branch,
            category
        )
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]