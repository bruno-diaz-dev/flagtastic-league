"""Persistence and division-eligibility rules for player rosters."""

import unicodedata

from database import get_connection

class PlayerAlreadyRegisteredInDivision(Exception):
    """Raised when a person already belongs to the requested division."""


class PlayerIdentityMismatch(Exception):
    """Raised when a document is already linked to a different person."""


class PlayerIdentityLocked(Exception):
    """Raised when a representative edits an identity shared beyond their team."""


def comparable_name(name):
    """Compare names without case, accents or repeated whitespace."""
    decomposed = unicodedata.normalize("NFKD", name or "")
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(stripped.casefold().split())


def _claimed_by_other_name(connection, player_row, name):
    """Whether an existing, account-owned identity carries a different name.

    A self-registered account owns its identity. Silently attaching a roster
    row with another name to it would let whoever registered a CURP first take
    over the real child's membership, so those rows are reported instead.
    """
    if player_row["inserted"] or comparable_name(player_row["name"]) == comparable_name(name):
        return False
    return connection.execute(
        "SELECT EXISTS (SELECT 1 FROM users WHERE player_id = %s) AS claimed",
        (player_row["id"],)
    ).fetchone()["claimed"]


def identity_is_shared(connection, player_id, team_id):
    """Whether the identity has its own account or another active roster."""
    return connection.execute(
        """
        SELECT EXISTS (SELECT 1 FROM users WHERE users.player_id = %s)
            OR EXISTS (
                SELECT 1 FROM team_players
                WHERE player_id = %s AND team_id <> %s AND active
            ) AS shared
        """,
        (player_id, player_id, team_id)
    ).fetchone()["shared"]


def create_player(team, player):
    """Create/reuse one player and idempotently attach them to a roster."""
    connection = get_connection()

    try:
        connection.execute("LOCK TABLE team_players IN SHARE ROW EXCLUSIVE MODE")

        existing_player = connection.execute(
            """
            INSERT INTO players (name, curp, age, identity_type, birth_date)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (curp) DO UPDATE
            SET curp = EXCLUDED.curp
            RETURNING id, name, age, identity_type, birth_date, (xmax = 0) AS inserted
            """,
            (player.name, player.curp, player.age, player.identity_type, player.birth_date)
        ).fetchone()

        if player.identity_type == "provisional" and (
            existing_player["identity_type"] != "provisional"
            or existing_player["birth_date"] != player.birth_date
            or existing_player["name"].strip().casefold() != player.name.strip().casefold()
        ):
            raise PlayerIdentityMismatch()
        if _claimed_by_other_name(connection, existing_player, player.name):
            raise PlayerIdentityMismatch()

        player_id = existing_player["id"]

        division_membership = connection.execute(
            """
            SELECT teams.id, teams.name, team_players.jersey_number
            FROM team_players
            JOIN teams ON teams.id = team_players.team_id
            WHERE team_players.player_id = %s
              AND teams.branch = %s
              AND teams.category = %s
              AND team_players.active
            LIMIT 1
            """,
            (player_id, team["branch"], team["category"])
        ).fetchone()

        if (
            division_membership is not None
            and division_membership["id"] != team["id"]
        ):
            raise PlayerAlreadyRegisteredInDivision()

        connection.execute(
            """
            INSERT INTO team_players (team_id, player_id, jersey_number)
            VALUES (%s, %s, %s)
            ON CONFLICT (team_id, player_id) DO UPDATE
            SET jersey_number = EXCLUDED.jersey_number,
                active = TRUE
            """,
            (team["id"], player_id, player.jersey_number)
        )

        connection.commit()
        return {
            "id": player_id,
            "team_id": team["id"],
            "name": existing_player["name"],
            "curp": player.curp,
            "age": existing_player["age"],
            "jersey_number": player.jersey_number
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def import_players(team, players):
    """Idempotently import roster rows without aborting on existing members."""
    connection = get_connection()
    created = 0
    updated = 0
    skipped = 0
    conflicts = []
    rows = []

    try:
        connection.execute("LOCK TABLE team_players IN SHARE ROW EXCLUSIVE MODE")

        for player in players:
            existing_player = connection.execute(
                """
                INSERT INTO players (name, curp, age, identity_type, birth_date)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (curp) DO UPDATE
                SET curp = EXCLUDED.curp
                RETURNING id, name, age, (xmax = 0) AS inserted
                """,
                (player.name, player.curp, player.age, player.identity_type, player.birth_date)
            ).fetchone()

            player_id = existing_player["id"]

            if _claimed_by_other_name(connection, existing_player, player.name):
                conflicts.append({
                    "player_id": player_id,
                    "name": player.name,
                    "reason": "identity_mismatch",
                })
                continue

            division_membership = connection.execute(
                """
                SELECT
                    team_players.team_id,
                    team_players.jersey_number,
                    teams.name AS team_name
                FROM team_players
                JOIN teams ON teams.id = team_players.team_id
                WHERE team_players.player_id = %s
                  AND teams.branch = %s
                  AND teams.category = %s
                  AND team_players.active
                LIMIT 1
                """,
                (player_id, team["branch"], team["category"])
            ).fetchone()

            if (
                division_membership is not None
                and division_membership["team_id"] != team["id"]
            ):
                conflicts.append({
                    "player_id": player_id,
                    "name": existing_player["name"],
                    "reason": "division_conflict",
                    "team_id": division_membership["team_id"],
                    "team_name": division_membership["team_name"],
                })
                continue

            jersey_owner = connection.execute(
                """
                SELECT players.id, players.name
                FROM team_players
                JOIN players ON players.id = team_players.player_id
                WHERE team_players.team_id = %s
                  AND team_players.jersey_number = %s
                  AND team_players.active
                  AND team_players.player_id <> %s
                LIMIT 1
                """,
                (team["id"], player.jersey_number, player_id)
            ).fetchone()

            if jersey_owner is not None:
                conflicts.append({
                    "player_id": player_id,
                    "name": existing_player["name"],
                    "reason": "jersey_conflict",
                    "jersey_number": player.jersey_number,
                    "existing_player_id": jersey_owner["id"],
                    "existing_player_name": jersey_owner["name"],
                })
                continue

            same_team = connection.execute(
                """
                SELECT jersey_number, active
                FROM team_players
                WHERE team_id = %s AND player_id = %s
                LIMIT 1
                """,
                (team["id"], player_id)
            ).fetchone()

            if (
                same_team is not None
                and same_team["active"]
                and same_team["jersey_number"] == player.jersey_number
            ):
                skipped += 1
                rows.append({
                    "id": player_id,
                    "team_id": team["id"],
                    "name": existing_player["name"],
                    "age": existing_player["age"],
                    "jersey_number": player.jersey_number,
                    "action": "skipped",
                })
                continue

            connection.execute(
                """
                INSERT INTO team_players (team_id, player_id, jersey_number)
                VALUES (%s, %s, %s)
                ON CONFLICT (team_id, player_id) DO UPDATE
                SET jersey_number = EXCLUDED.jersey_number,
                    active = TRUE
                """,
                (team["id"], player_id, player.jersey_number)
            )

            action = "created" if same_team is None else "updated"
            if action == "created":
                created += 1
            else:
                updated += 1

            rows.append({
                "id": player_id,
                "team_id": team["id"],
                "name": existing_player["name"],
                "age": existing_player["age"],
                "jersey_number": player.jersey_number,
                "action": action,
            })

        connection.commit()
        return {
            "imported": created,
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "conflicts": conflicts,
            "rows": rows,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_players_by_team(team_id):
    """Return a team's public roster ordered by jersey number."""
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            players.id,
            team_players.team_id,
            players.name,
            players.aka,
            players.age,
            CASE
                WHEN players.profile_photo_path IS NULL THEN NULL
                ELSE '/media/profiles/' || players.profile_photo_path
            END AS profile_photo_url,
            team_players.jersey_number
        FROM team_players
        JOIN players
            ON players.id = team_players.player_id
        WHERE team_players.team_id = %s
          AND team_players.active
        ORDER BY team_players.jersey_number
        """,
        (team_id,)
    ).fetchall()

    connection.close()

    return[dict(row) for row in rows]


def search_registered_players(team, query, limit=20):
    """Find eligible player identities without exposing private fields."""
    connection = get_connection()
    pattern = f"%{query.strip()}%"
    rows = connection.execute(
        """
        SELECT players.id, players.name, players.aka, players.age,
               CASE WHEN players.profile_photo_path IS NULL THEN NULL
                    ELSE '/media/profiles/' || players.profile_photo_path
               END AS profile_photo_url,
               EXISTS (
                   SELECT 1 FROM users
                   WHERE users.player_id = players.id
                     AND users.status = 'active'
               ) AS has_account
        FROM players
        WHERE (
              players.name ILIKE %s
              OR COALESCE(players.aka, '') ILIKE %s
          )
          AND NOT EXISTS (
              SELECT 1
              FROM team_players
              JOIN teams ON teams.id = team_players.team_id
              WHERE team_players.player_id = players.id
                AND team_players.active
                AND teams.branch = %s
                AND teams.category = %s
          )
        ORDER BY COALESCE(NULLIF(players.aka, ''), players.name), players.name
        LIMIT %s
        """,
        (pattern, pattern, team["branch"], team["category"], limit)
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def join_registered_player(player_id, team, jersey_number, curp=None):
    """Attach an existing player identity to a managed team atomically.

    When ``curp`` is given it must equal the identity's stored document;
    otherwise the player is reported as not found, without revealing which of
    the two did not match.
    """
    connection = get_connection()
    try:
        # Same lock as create_player/import_players: serializes the
        # one-player-per-division check against concurrent joins.
        connection.execute("LOCK TABLE team_players IN SHARE ROW EXCLUSIVE MODE")
        existing_player = connection.execute(
            """
            SELECT players.id, players.curp
            FROM players
            WHERE players.id = %s
            FOR UPDATE OF players
            """,
            (player_id,)
        ).fetchone()
        if existing_player is None:
            return None
        if curp is not None and (existing_player["curp"] or "").strip().upper() != curp:
            return None

        conflict = connection.execute(
            """
            SELECT 1
            FROM team_players
            JOIN teams ON teams.id = team_players.team_id
            WHERE team_players.player_id = %s
              AND teams.branch = %s
              AND teams.category = %s
              AND team_players.active
            """,
            (player_id, team["branch"], team["category"])
        ).fetchone()
        if conflict is not None:
            raise PlayerAlreadyRegisteredInDivision()

        membership = connection.execute(
            """
            INSERT INTO team_players (team_id, player_id, jersey_number)
            VALUES (%s, %s, %s)
            ON CONFLICT (team_id, player_id) DO UPDATE
            SET jersey_number = EXCLUDED.jersey_number, active = TRUE
            RETURNING team_id, player_id, jersey_number
            """,
            (team["id"], player_id, jersey_number)
        ).fetchone()
        connection.commit()
        return dict(membership)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_managed_roster_player(team_id, player_id):
    """Return private edit fields only for an active team membership."""
    connection = get_connection()
    row = connection.execute(
        """
        SELECT players.id, players.name, players.curp, players.age,
               players.identity_type, players.birth_date,
               team_players.jersey_number
        FROM team_players
        JOIN players ON players.id = team_players.player_id
        WHERE team_players.team_id = %s
          AND team_players.player_id = %s
          AND team_players.active
        """,
        (team_id, player_id)
    ).fetchone()
    connection.close()
    return dict(row) if row is not None else None


def update_roster_player_photo(team_id, player_id, photo, can_edit_shared_identity=False):
    """Replace a player's photo only when they belong to the managed team.

    Representatives cannot replace the photo of a player who has their own
    account or plays on another team; that identity is not theirs to change.
    """
    connection = get_connection()
    try:
        if not can_edit_shared_identity and identity_is_shared(connection, player_id, team_id):
            member = connection.execute(
                "SELECT 1 FROM team_players WHERE team_id = %s AND player_id = %s AND active",
                (team_id, player_id)
            ).fetchone()
            if member is not None:
                raise PlayerIdentityLocked()
        updated = connection.execute(
            """
            UPDATE players
            SET profile_photo_path = %s,
                profile_photo_data = %s,
                profile_photo_type = %s
            WHERE id = %s
              AND EXISTS (
                  SELECT 1 FROM team_players
                  WHERE team_players.team_id = %s
                    AND team_players.player_id = players.id
                    AND team_players.active
              )
            RETURNING id
            """,
            (
                photo["filename"],
                photo["content"],
                photo["media_type"],
                player_id,
                team_id
            )
        ).fetchone()
        connection.commit()
        return updated is not None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def update_roster_player(team_id, player_id, player, can_edit_shared_identity=False):
    """Correct an active roster identity and its team-specific jersey.

    The jersey always belongs to the team. The identity (name, document and
    birth date) is shared: a representative may change it only while the
    player has no account and no other active roster.
    """
    connection = get_connection()
    try:
        current = connection.execute(
            """
            SELECT players.id, players.name, players.age, players.curp,
                   players.identity_type, players.birth_date
            FROM team_players
            JOIN players ON players.id = team_players.player_id
            WHERE team_players.team_id = %s AND team_players.player_id = %s
              AND team_players.active
            FOR UPDATE OF players
            """,
            (team_id, player_id)
        ).fetchone()
        if current is None:
            return None

        identity_type = player.identity_type or "curp"
        identity_changed = (
            player.name.strip() != (current["name"] or "").strip()
            or player.curp != (current["curp"] or "").strip().upper()
            or identity_type != (current["identity_type"] or "curp")
            or (identity_type == "provisional" and player.birth_date != current["birth_date"])
        )
        if (
            identity_changed
            and not can_edit_shared_identity
            and identity_is_shared(connection, player_id, team_id)
        ):
            raise PlayerIdentityLocked()

        if identity_changed:
            updated = connection.execute(
                """
                UPDATE players
                SET name = %s, curp = %s, age = %s, identity_type = %s, birth_date = %s
                WHERE id = %s
                RETURNING id, name, age
                """,
                (player.name, player.curp, player.age, player.identity_type, player.birth_date, player_id)
            ).fetchone()
        else:
            updated = {"id": current["id"], "name": current["name"], "age": current["age"]}
        connection.execute(
            """
            UPDATE team_players
            SET jersey_number = %s
            WHERE team_id = %s AND player_id = %s AND active
            """,
            (player.jersey_number, team_id, player_id)
        )
        connection.commit()
        return {
            **dict(updated),
            "team_id": team_id,
            "jersey_number": player.jersey_number
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def deactivate_roster_player(team_id, player_id):
    """Remove a player from the current roster without deleting history."""
    connection = get_connection()
    try:
        removed = connection.execute(
            """
            UPDATE team_players
            SET active = FALSE
            WHERE team_id = %s AND player_id = %s AND active
            RETURNING player_id
            """,
            (team_id, player_id)
        ).fetchone()
        connection.commit()
        return removed is not None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def join_team(player_id, team, jersey_number):
    """Attach an existing player identity to one eligible division roster."""
    connection = get_connection()
    try:
        connection.execute("LOCK TABLE team_players IN SHARE ROW EXCLUSIVE MODE")
        conflict = connection.execute(
            """
            SELECT 1
            FROM team_players
            JOIN teams ON teams.id = team_players.team_id
            WHERE team_players.player_id = %s
              AND teams.branch = %s
              AND teams.category = %s
              AND team_players.active
            """,
            (player_id, team["branch"], team["category"])
        ).fetchone()
        if conflict is not None:
            raise PlayerAlreadyRegisteredInDivision()

        membership = connection.execute(
            """
            INSERT INTO team_players (team_id, player_id, jersey_number)
            VALUES (%s, %s, %s)
            ON CONFLICT (team_id, player_id) DO UPDATE
            SET jersey_number = EXCLUDED.jersey_number,
                active = TRUE
            RETURNING team_id, player_id, jersey_number
            """,
            (team["id"], player_id, jersey_number)
        ).fetchone()
        connection.commit()
        return dict(membership)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
