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
          AND users.status = 'active'
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


def get_public_referee_profile(user_id):
    """Return a referee identity with non-sensitive assignment aggregates."""
    profile = get_referee_profile(user_id)
    if profile is None:
        return None

    connection = get_connection()
    summary = connection.execute(
        """
        SELECT COUNT(DISTINCT game_referees.game_id)::INTEGER AS games,
               COUNT(DISTINCT games.week)::INTEGER AS weeks,
               COUNT(DISTINCT game_referees.game_id)
                   FILTER (WHERE games.status = 'completed')::INTEGER
                   AS completed_games
        FROM game_referees
        JOIN games ON games.id = game_referees.game_id
        WHERE game_referees.user_id = %s
        """,
        (user_id,)
    ).fetchone()
    positions = connection.execute(
        """
        SELECT game_referees.position,
               COUNT(DISTINCT game_referees.game_id)::INTEGER AS games
        FROM game_referees
        WHERE game_referees.user_id = %s
        GROUP BY game_referees.position
        ORDER BY CASE game_referees.position
            WHEN 'referee' THEN 1
            WHEN 'down_judge' THEN 2
            WHEN 'field_judge' THEN 3
            WHEN 'side_judge' THEN 4
            WHEN 'statistician' THEN 5
            ELSE 6
        END
        """,
        (user_id,)
    ).fetchall()
    connection.close()

    profile.pop("player_id", None)
    profile["statistics"] = {
        "games": summary["games"],
        "completed_games": summary["completed_games"],
        "weeks": summary["weeks"],
        "positions": [dict(position) for position in positions],
    }
    return profile


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
