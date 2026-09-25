"""Persistence operations for league teams."""

from database import get_connection

def create_team(team, representative_user_id=None):
    """Create a normalized pending team and return its public fields."""
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

        # A representative automatically manages a team they create.
        if representative_user_id is not None:
            connection.execute(
                """
                INSERT INTO team_representatives (user_id, team_id)
                VALUES (%s, %s)
                """,
                (representative_user_id, team_id)
            )

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
    """Return all teams in stable creation order."""
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
    """Return a team by identifier, or None when it does not exist."""
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


def delete_team(team_id):
    """Delete one team and cascade its memberships, games, and statistics."""
    connection = get_connection()
    try:
        deleted = connection.execute(
            "DELETE FROM teams WHERE id = %s RETURNING id",
            (team_id,)
        ).fetchone()
        connection.commit()
        return deleted is not None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_represented_team_ids(user_id):
    """Return the teams explicitly managed by one representative account."""
    connection = get_connection()
    rows = connection.execute(
        "SELECT team_id FROM team_representatives WHERE user_id = %s",
        (user_id,)
    ).fetchall()
    connection.close()
    return [row["team_id"] for row in rows]
