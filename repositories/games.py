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
            games.id,
            games.home_score,
            games.away_score,
            home_team.id AS "home_team_id",
            home_team.name AS "home_team_name",
            away_team.id AS "away_team_id",
            away_team.name AS "away_team_name"
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
                "name": row["home_team_name"]
            },

            "away_team": {
                "id": row["away_team_id"],
                "name": row["away_team_name"]
            },
            "home_score": row["home_score"],
            "away_score": row["away_score"]
        }
        for row in rows
    ]


def update_game_score(game_id, score):
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