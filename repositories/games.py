"""Persistence operations for games and final scores."""

from database import get_connection

def create_game(game):
    """Create an unscored game between two validated teams."""
    connection = get_connection()

    try:
        created_game = connection.execute(
            """
            INSERT INTO games (
                home_team_id,
                away_team_id,
                week,
                field_number,
                start_time
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING
                id,
                home_team_id,
                away_team_id,
                week,
                field_number,
                start_time
            """,
            (
                game.home_team_id,
                game.away_team_id,
                game.week,
                game.field_number,
                game.start_time
            )
        ).fetchone()

        connection.commit()

        return dict(created_game)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def get_games():
    """Return games with nested public summaries for both teams."""
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            games.id,
            games.home_score,
            games.away_score,
            games.week,
            games.field_number,
            games.start_time,
            home_team.id AS "home_team_id",
            home_team.name AS "home_team_name",
            home_team.branch AS "home_team_branch",
            home_team.category AS "home_team_category",
            away_team.id AS "away_team_id",
            away_team.name AS "away_team_name",
            away_team.branch AS "away_team_branch",
            away_team.category AS "away_team_category"
        FROM games
        JOIN teams AS home_team
            ON games.home_team_id = home_team.id
        JOIN teams AS away_team
            ON games.away_team_id = away_team.id
        ORDER BY games.id
        """
    ).fetchall()

    connection.close()

    return [
        {
            "id": row["id"],
            "home_team": {
                "id": row["home_team_id"],
                "name": row["home_team_name"],
                "branch": row["home_team_branch"],
                "category": row["home_team_category"]
            },

            "away_team": {
                "id": row["away_team_id"],
                "name": row["away_team_name"],
                "branch": row["away_team_branch"],
                "category": row["away_team_category"]
            },
            "home_score": row["home_score"],
            "away_score": row["away_score"],
            "week": row["week"],
            "field_number": row["field_number"],
            "start_time": row["start_time"]
        }
        for row in rows
    ]


def update_game_score(game_id, score):
    """Store a final score and return the game, or None when missing."""
    connection = get_connection()

    try:
        updated_game = connection.execute(
            """
            UPDATE games
            SET
                home_score = %s,
                away_score = %s
            WHERE id = %s
            RETURNING
                id,
                home_team_id,
                away_team_id,
                home_score,
                away_score
            """,
            (
                score.home_score,
                score.away_score,
                game_id
            )
        ).fetchone()

        connection.commit()

        return (
            dict(updated_game)
            if updated_game is not None
            else None
        )

    except Exception:
        connection.rollback()
        raise


    finally:
        connection.close()


def assign_referee(game_id, user_id, position, assigned_by):
    """Assign an official to one named slot, replacing that slot atomically."""
    connection = get_connection()
    try:
        # A role sheet has one person per position. Reassigning a position is
        # intentional and should not leave the previous official attached.
        connection.execute(
            "DELETE FROM game_referees WHERE game_id = %s AND position = %s",
            (game_id, position)
        )
        row = connection.execute(
            """
            INSERT INTO game_referees (game_id, user_id, position, assigned_by)
            VALUES (%s, %s, %s, %s)
            RETURNING game_id, user_id, position, assigned_by, assigned_at
            """,
            (game_id, user_id, position, assigned_by)
        ).fetchone()
        connection.commit()
        return dict(row)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_game_referee(game_id, user_id):
    """Return one referee assignment, or None."""
    connection = get_connection()
    row = connection.execute(
        """
        SELECT game_id, user_id, position, assigned_by, assigned_at
        FROM game_referees WHERE game_id = %s AND user_id = %s
        """,
        (game_id, user_id)
    ).fetchone()
    connection.close()
    return dict(row) if row is not None else None


def remove_referee(game_id, user_id):
    """Remove an assignment while leaving the game intact."""
    connection = get_connection()
    deleted = connection.execute(
        "DELETE FROM game_referees WHERE game_id = %s AND user_id = %s RETURNING 1",
        (game_id, user_id)
    ).fetchone()
    connection.commit()
    connection.close()
    return deleted is not None


def get_game_referees(game_id):
    """List assigned referees for league administration."""
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT users.id, users.name, users.email, players.aka,
               COALESCE(NULLIF(players.aka, ''), users.name) AS display_name,
               game_referees.position, game_referees.assigned_at,
               game_referees.assigned_by
        FROM game_referees
        JOIN users ON users.id = game_referees.user_id
        LEFT JOIN players ON players.id = users.player_id
        WHERE game_referees.game_id = %s
        ORDER BY CASE game_referees.position
            WHEN 'referee' THEN 1 WHEN 'down_judge' THEN 2
            WHEN 'field_judge' THEN 3 WHEN 'side_judge' THEN 4
            WHEN 'statistician' THEN 5 END
        """,
        (game_id,)
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def get_games_for_referee(user_id):
    """Return only games assigned to the authenticated referee."""
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT
            games.id,
            games.home_score,
            games.away_score,
            games.week,
            games.field_number,
            games.start_time,
            game_referees.position AS official_position,
            home_team.id AS home_team_id,
            home_team.name AS home_team_name,
            home_team.branch AS home_team_branch,
            home_team.category AS home_team_category,
            away_team.id AS away_team_id,
            away_team.name AS away_team_name,
            away_team.branch AS away_team_branch,
            away_team.category AS away_team_category
        FROM game_referees
        JOIN games ON games.id = game_referees.game_id
        JOIN teams AS home_team ON home_team.id = games.home_team_id
        JOIN teams AS away_team ON away_team.id = games.away_team_id
        WHERE game_referees.user_id = %s
        ORDER BY games.week, games.id
        """,
        (user_id,)
    ).fetchall()
    connection.close()
    return [
        {
            "id": row["id"],
            "home_team": {
                "id": row["home_team_id"],
                "name": row["home_team_name"],
                "branch": row["home_team_branch"],
                "category": row["home_team_category"]
            },
            "away_team": {
                "id": row["away_team_id"],
                "name": row["away_team_name"],
                "branch": row["away_team_branch"],
                "category": row["away_team_category"]
            },
            "home_score": row["home_score"],
            "away_score": row["away_score"],
            "week": row["week"],
            "field_number": row["field_number"],
            "start_time": row["start_time"],
            "official_position": row["official_position"]
        }
        for row in rows
    ]


def apply_referee_schedule(assignments, assigned_by):
    """Atomically replace reviewed fields and referees for selected games."""
    connection = get_connection()
    try:
        for assignment in assignments:
            updated = connection.execute(
                """
                UPDATE games
                SET field_number = %s,
                    start_time = COALESCE(%s, start_time)
                WHERE id = %s RETURNING id
                """,
                (
                    assignment.field_number,
                    assignment.scheduled_time,
                    assignment.game_id
                )
            ).fetchone()
            if updated is None:
                raise ValueError(f"No existe el partido {assignment.game_id}")
            connection.execute(
                "DELETE FROM game_referees WHERE game_id = %s",
                (assignment.game_id,)
            )
            for official in assignment.officials:
                connection.execute(
                    """
                    INSERT INTO game_referees
                        (game_id, user_id, position, assigned_by)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        assignment.game_id,
                        official.user_id,
                        official.position,
                        assigned_by
                    )
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
