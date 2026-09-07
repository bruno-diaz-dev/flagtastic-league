from database import get_connection

class PlayerAlreadyRegisteredInDivision(Exception):
    pass

def create_player(team, player):
    connection = get_connection()

    try:
        existing_player = connection.execute(
            """
            SELECT
                id,
                name,
                age
            FROM players
            WHERE curp = %s
            """,
            (player.curp,)
        ).fetchone()

        if existing_player is None:
            existing_player = connection.execute(
                """
                INSERT INTO players (
                    name,
                    curp,
                    age
                )
                VALUES (%s, %s, %s)
                RETURNING id, name, age
                """,
                (
                    player.name,
                    player.curp,
                    player.age
                )
            ).fetchone()

        player_id = existing_player["id"]

        division_conflict = connection.execute(
            """
            SELECT
                teams.id,
                teams.name
            FROM team_players
            JOIN teams
                ON teams.id = team_players.team_id
            WHERE team_players.player_id = %s
                AND teams.branch = %s
                AND teams.category = %s
            LIMIT 1
            """,
            (
                player_id,
                team["branch"],
                team["category"]
            )
        ).fetchone()

        if division_conflict is not None:
            raise PlayerAlreadyRegisteredInDivision()

        connection.execute(
            f"""
            INSERT INTO team_players (
                team_id,
                player_id,
                jersey_number
            )
            VALUES (%s, %s, %s)
            """,
            (
                team["id"],
                player_id,
                player.jersey_number
            )
        )

        connection.commit()

        return {
            "id": player_id,
            "team_id": team["id"],
            "name": existing_player["name"],
            "curp": player.curp,
            "age": player.age,
            "jersey_number": player.jersey_number
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def get_players_by_team(team_id):
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            players.id,
            team_players.team_id,
            players.name,
            players.age,
            team_players.jersey_number
        FROM team_players
        JOIN players
            ON players.id = team_players.player_id
        WHERE team_players.team_id = %s
        ORDER BY team_players.jersey_number
        """,
        (team_id,)
    ).fetchall()

    connection.close()

    return[dict(row) for row in rows]