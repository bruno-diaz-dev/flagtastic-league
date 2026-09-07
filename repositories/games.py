from database import get_connection

def create_game(game):
    connection = get_connection()

    try:
        created_game = connection.execute(
            """
            INSERT INTO games (
                home_team_id,
                away_team_id
            )
            VALUES (%s, %s)
            RETURNING
                id,
                home_team_id,
                away_team_id
            """,
            (
                game.home_team_id,
                game.away_team_id
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
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            id,
            home_team_id,
            away_team_id
        FROM games
        ORDER BY id
        """
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]