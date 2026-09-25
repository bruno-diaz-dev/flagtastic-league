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
            "status": "pending",
            "logo_url": None
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
        SELECT id, name, branch, category, status,
               logo_data IS NOT NULL AS has_logo
        FROM teams
        ORDER BY id
        """
    ).fetchall()

    connection.close()

    return [_public_team(row) for row in rows]

def get_team_by_id(team_id):
    """Return a team by identifier, or None when it does not exist."""
    connection = get_connection()

    row = connection.execute(
        """
        SELECT id, name, branch, category, status,
               logo_data IS NOT NULL AS has_logo
        FROM teams
        WHERE id = %s
        """,
        (team_id,)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return _public_team(row)


def _public_team(row):
    """Expose a stable logo URL without returning image bytes in JSON."""
    team = dict(row)
    has_logo = team.pop("has_logo", False)
    team["logo_url"] = f"/api/teams/{team['id']}/logo" if has_logo else None
    return team


def update_team_logo(team_id, content, media_type):
    """Persist a validated logo directly with its team."""
    connection = get_connection()
    try:
        row = connection.execute(
            """
            UPDATE teams SET logo_data = %s, logo_type = %s
            WHERE id = %s RETURNING id
            """,
            (content, media_type, team_id)
        ).fetchone()
        connection.commit()
        return row is not None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_team_logo(team_id):
    """Return stored logo bytes and media type without exposing other fields."""
    connection = get_connection()
    row = connection.execute(
        "SELECT logo_data, logo_type FROM teams WHERE id = %s",
        (team_id,)
    ).fetchone()
    connection.close()
    if row is None or row["logo_data"] is None:
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
