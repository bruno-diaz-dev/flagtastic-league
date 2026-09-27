"""Persistence and division-eligibility rules for player rosters."""

from database import get_connection

class PlayerAlreadyRegisteredInDivision(Exception):
    """Raised when a person already belongs to the requested division."""

def create_player(team, player):
    """Create or reuse a person and attach them to an eligible team roster."""
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

        # CURP identifies a person globally; roster membership is stored separately.
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

        # A person may join multiple divisions, but only one team per division.
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
                AND team_players.active
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
            ON CONFLICT (team_id, player_id) DO UPDATE
            SET jersey_number = EXCLUDED.jersey_number,
                active = TRUE
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


def import_players(team, players):
    """Atomically create or reuse players and add them to one team roster."""
    connection = get_connection()
    imported = []

    try:
        for player in players:
            existing_player = connection.execute(
                """
                SELECT id, name, age
                FROM players
                WHERE curp = %s
                """,
                (player.curp,)
            ).fetchone()

            if existing_player is None:
                existing_player = connection.execute(
                    """
                    INSERT INTO players (name, curp, age)
                    VALUES (%s, %s, %s)
                    RETURNING id, name, age
                    """,
                    (player.name, player.curp, player.age)
                ).fetchone()

            player_id = existing_player["id"]

            division_conflict = connection.execute(
                """
                SELECT teams.id, teams.name
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

            if division_conflict is not None:
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

            imported.append({
                "id": player_id,
                "team_id": team["id"],
                "name": existing_player["name"],
                "age": existing_player["age"],
                "jersey_number": player.jersey_number
            })

        connection.commit()
        return imported

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


def get_managed_roster_player(team_id, player_id):
    """Return private edit fields only for an active team membership."""
    connection = get_connection()
    row = connection.execute(
        """
        SELECT players.id, players.name, players.curp, players.age,
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


def update_roster_player_photo(team_id, player_id, photo):
    """Replace a player's photo only when they belong to the managed team."""
    connection = get_connection()
    try:
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


def update_roster_player(team_id, player_id, player):
    """Correct an active roster identity and its team-specific jersey."""
    connection = get_connection()
    try:
        membership = connection.execute(
            """
            SELECT 1 FROM team_players
            WHERE team_id = %s AND player_id = %s AND active
            """,
            (team_id, player_id)
        ).fetchone()
        if membership is None:
            return None

        updated = connection.execute(
            """
            UPDATE players
            SET name = %s, curp = %s, age = %s
            WHERE id = %s
            RETURNING id, name, age
            """,
            (player.name, player.curp, player.age, player_id)
        ).fetchone()
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
