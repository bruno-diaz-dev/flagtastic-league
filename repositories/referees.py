"""Persistence for the authenticated referee directory and profile photos."""

from database import get_connection


def get_referee_roster():
    """Return active users who have the cumulative referee role."""
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT users.id, users.name,
               COALESCE(NULLIF(users.aka, ''), NULLIF(players.aka, '')) AS aka,
               COALESCE(
                   NULLIF(users.aka, ''),
                   NULLIF(players.aka, ''),
                   users.name
               ) AS display_name,
               CASE
                   WHEN players.profile_photo_path IS NOT NULL
                       THEN '/media/profiles/' || players.profile_photo_path
                   WHEN users.profile_photo_path IS NOT NULL
                       THEN '/media/profiles/' || users.profile_photo_path
                   ELSE NULL
               END AS profile_photo_url
        FROM users
        LEFT JOIN players ON players.id = users.player_id
        WHERE users.status = 'active'
          AND EXISTS (
              SELECT 1
              FROM user_roles
              WHERE user_roles.user_id = users.id
                AND user_roles.role = 'referee'
          )
        ORDER BY COALESCE(
            NULLIF(users.aka, ''),
            NULLIF(players.aka, ''),
            users.name
        ), users.id
        """
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def get_referee_match_candidates():
    """Return active accounts allowed to officiate, including multi-role users."""
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT users.id, users.name,
               COALESCE(NULLIF(users.aka, ''), NULLIF(players.aka, '')) AS aka,
               COALESCE(
                   NULLIF(users.aka, ''),
                   NULLIF(players.aka, ''),
                   users.name
               ) AS display_name
        FROM users
        LEFT JOIN players ON players.id = users.player_id
        WHERE users.status = 'active'
          AND EXISTS (
              SELECT 1
              FROM user_roles
              WHERE user_roles.user_id = users.id
                AND user_roles.role = 'referee'
          )
        ORDER BY COALESCE(
            NULLIF(users.aka, ''),
            NULLIF(players.aka, ''),
            users.name
        ), users.id
        """
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def get_referee_profile(user_id):
    """Return the effective referee photo and whether this account may upload it."""
    connection = get_connection()
    row = connection.execute(
        """
        SELECT users.id, users.name, users.player_id,
               COALESCE(NULLIF(users.aka, ''), NULLIF(players.aka, '')) AS aka,
               COALESCE(
                   NULLIF(users.aka, ''),
                   NULLIF(players.aka, ''),
                   users.name
               ) AS display_name,
               CASE
                   WHEN players.profile_photo_path IS NOT NULL
                       THEN '/media/profiles/' || players.profile_photo_path
                   WHEN users.profile_photo_path IS NOT NULL
                       THEN '/media/profiles/' || users.profile_photo_path
                   ELSE NULL
               END AS profile_photo_url
        FROM users
        LEFT JOIN players ON players.id = users.player_id
        WHERE users.id = %s
          AND EXISTS (
              SELECT 1
              FROM user_roles
              WHERE user_roles.user_id = users.id
                AND user_roles.role = 'referee'
          )
        """,
        (user_id,)
    ).fetchone()
    connection.close()
    return dict(row) if row is not None else None


def update_referee_aka(user_id, aka):
    """Store one effective referee AKA on the linked identity when available."""
    connection = get_connection()
    try:
        user = connection.execute(
            """
            SELECT users.player_id
            FROM users
            WHERE users.id = %s
              AND EXISTS (
                  SELECT 1
                  FROM user_roles
                  WHERE user_roles.user_id = users.id
                    AND user_roles.role = 'referee'
              )
            FOR UPDATE
            """,
            (user_id,)
        ).fetchone()
        if user is None:
            return False
        if user["player_id"] is not None:
            connection.execute(
                "UPDATE players SET aka = %s WHERE id = %s",
                (aka, user["player_id"])
            )
            connection.execute(
                "UPDATE users SET aka = NULL WHERE id = %s",
                (user_id,)
            )
        else:
            connection.execute(
                "UPDATE users SET aka = %s WHERE id = %s",
                (aka, user_id)
            )
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def update_referee_photo(user_id, photo):
    """Store the photo on the player identity when available, otherwise the user."""
    connection = get_connection()
    try:
        user = connection.execute(
            """
            SELECT users.player_id
            FROM users
            WHERE users.id = %s
              AND EXISTS (
                  SELECT 1
                  FROM user_roles
                  WHERE user_roles.user_id = users.id
                    AND user_roles.role = 'referee'
              )
            FOR UPDATE
            """,
            (user_id,)
        ).fetchone()
        if user is None:
            return False
        parameters = (photo["filename"], photo["content"], photo["media_type"])
        if user["player_id"] is not None:
            connection.execute(
                """
                UPDATE players
                SET profile_photo_path = %s,
                    profile_photo_data = %s,
                    profile_photo_type = %s
                WHERE id = %s
                """,
                (*parameters, user["player_id"])
            )
        else:
            connection.execute(
                """
                UPDATE users
                SET profile_photo_path = %s,
                    profile_photo_data = %s,
                    profile_photo_type = %s
                WHERE id = %s
                """,
                (*parameters, user_id)
            )
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
