from database import get_connection

def create_team(team):
    connection = get_connection()

    name = team.name.strip()
    branch = team.branch.strip().lower()
    category = team.category.strip().lower()

    try:
        cursor = connection.execute(
            """
            INSERT INTO teams (
                name,
                branch,
                category,
                status
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                name,
                branch,
                category,
                "pending"
            )
        )

        team_id = cursor.fetchone()["id"]

        connection.commit()

        return {
            "id": team_id,
            "name": name,
            "branch": branch,
            "category": category,
            "status": "pending"
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def get_all_teams():
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT *
        FROM teams
        ORDER BY id
        """
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]

def get_team_by_id(team_id):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT *
        FROM teams
        WHERE id = %s
        """,
        (team_id,)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return dict(row)