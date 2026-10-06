"""Persistence operations for games and final scores."""

from database import get_connection


class ScheduleConflictError(ValueError):
    """A schedule replacement would discard or misattribute existing data."""


class GameStateConflictError(ValueError):
    """The requested transition conflicts with the current game state."""


def resolve_game_participants(connection, game):
    """Resolve invited identities inside the same transaction as the schedule."""
    from services.divisions import teams_share_game_division
    known = {}
    for side in ("home", "away"):
        team_id = getattr(game, side + "_team_id")
        if team_id:
            team = connection.execute("SELECT id, name, branch, category, is_guest FROM teams WHERE id = %s", (team_id,)).fetchone()
            if team is None:
                raise ScheduleConflictError("Equipo no encontrado")
            if team["is_guest"] and not game.is_friendly:
                raise ScheduleConflictError("Los invitados solo pueden participar en amistosos")
            known[side] = dict(team)
    if len(known) == 2 and not teams_share_game_division(known["home"], known["away"]):
        raise ScheduleConflictError("Los equipos deben pertenecer a la misma rama y categoria; U8, U10 y U12 permiten cruces entre ramas")
    reference = next(iter(known.values()), None)
    branch = reference["branch"] if reference else game.branch
    category = reference["category"] if reference else game.category
    for side in ("home", "away"):
        if side in known:
            continue
        name = getattr(game, side + "_guest_name")
        row = connection.execute(
            """INSERT INTO teams (name, branch, category, status, is_guest)
               VALUES (%s, %s, %s, 'inactive', TRUE)
               ON CONFLICT (LOWER(BTRIM(name)), branch, category) DO UPDATE SET name = teams.name
               RETURNING id, name, branch, category, is_guest""",
            (name, branch, category),
        ).fetchone()
        known[side] = dict(row)
    if known["home"]["id"] == known["away"]["id"]:
        raise ScheduleConflictError("Un equipo no puede jugar contra si mismo")
    return game.model_copy(update={"home_team_id": known["home"]["id"], "away_team_id": known["away"]["id"]})


def create_game(game):
    """Create the fixture and any invited teams atomically."""
    with get_connection() as connection:
        game = resolve_game_participants(connection, game)
        row = connection.execute(
            """INSERT INTO games (home_team_id, away_team_id, week, field_number, start_time, is_friendly)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING id, home_team_id, away_team_id, week, field_number, start_time, status, is_friendly""",
            (game.home_team_id, game.away_team_id, game.week, game.field_number, game.start_time, game.is_friendly),
        ).fetchone()
        return dict(row)


def import_game_schedule(games):
    """Upsert reviewed schedule rows by their week, field, and start time."""
    connection = get_connection()
    created = 0
    updated = 0
    skipped = 0
    try:
        # Serialize schedule imports, including empty slots, until commit.
        connection.execute("LOCK TABLE games IN SHARE ROW EXCLUSIVE MODE")
        for game in games:
            game = resolve_game_participants(connection, game)
            existing = connection.execute(
                """
                SELECT id, home_team_id, away_team_id, home_score, away_score, is_friendly
                FROM games
                WHERE week = %s
                  AND field_number = %s
                  AND start_time IS NOT DISTINCT FROM %s
                ORDER BY id
                LIMIT 1
                """,
                (game.week, game.field_number, game.start_time),
            ).fetchone()

            if existing is not None:
                if (
                    existing["home_team_id"] == game.home_team_id
                    and existing["away_team_id"] == game.away_team_id
                    and existing["is_friendly"] == game.is_friendly
                ):
                    skipped += 1
                    continue

                related = connection.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM player_week_stats WHERE game_id = %s
                        UNION ALL
                        SELECT 1 FROM game_referees WHERE game_id = %s
                        UNION ALL
                        SELECT 1 FROM game_live_sessions WHERE game_id = %s
                    ) AS present
                    """,
                    (existing["id"], existing["id"], existing["id"]),
                ).fetchone()["present"]
                if existing["home_score"] is not None or existing["away_score"] is not None or related:
                    raise ScheduleConflictError(
                        f"El partido {existing['id']} ya tiene resultados, estadisticas "
                        "o arbitros asignados. No se pueden reemplazar sus equipos."
                    )

                connection.execute(
                    """
                    UPDATE games
                    SET home_team_id = %s,
                        away_team_id = %s, is_friendly = %s
                    WHERE id = %s
                    """,
                    (
                        game.home_team_id,
                        game.away_team_id,
                        game.is_friendly,
                        existing["id"],
                    ),
                )
                updated += 1
                continue

            connection.execute(
                """
                INSERT INTO games
                    (home_team_id, away_team_id, week, field_number, start_time, is_friendly)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    game.home_team_id,
                    game.away_team_id,
                    game.week,
                    game.field_number,
                    game.start_time,
                    game.is_friendly,
                ),
            )
            created += 1
        connection.commit()
        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def get_games():
    """Return games with nested public summaries for both teams."""
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            games.id,
            games.home_score,
            games.away_score,
            games.week,
            games.field_number,
            games.start_time,
            games.status,
            games.is_friendly,
            home_team.is_guest AS home_is_guest,
            home_team.id AS "home_team_id",
            home_team.name AS "home_team_name",
            home_team.branch AS "home_team_branch",
            home_team.category AS "home_team_category",
            home_team.logo_version AS "home_team_has_logo",
            away_team.is_guest AS away_is_guest,
            away_team.id AS "away_team_id",
            away_team.name AS "away_team_name",
            away_team.branch AS "away_team_branch",
            away_team.category AS "away_team_category",
            away_team.logo_version AS "away_team_has_logo"
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
                "id": row["home_team_id"], "is_guest": row["home_is_guest"],
                "name": row["home_team_name"],
                "branch": row["home_team_branch"],
                "category": row["home_team_category"],
                **(
                    {"logo_url": f"/api/teams/{row['home_team_id']}/logo?v={row['home_team_has_logo']}&size=256"}
                    if row["home_team_has_logo"] else {}
                )
            },

            "away_team": {
                "id": row["away_team_id"], "is_guest": row["away_is_guest"],
                "name": row["away_team_name"],
                "branch": row["away_team_branch"],
                "category": row["away_team_category"],
                **(
                    {"logo_url": f"/api/teams/{row['away_team_id']}/logo?v={row['away_team_has_logo']}&size=256"}
                    if row["away_team_has_logo"] else {}
                )
            },
            "home_score": row["home_score"],
            "away_score": row["away_score"],
            "week": row["week"],
            "field_number": row["field_number"],
            "start_time": row["start_time"],
            "status": row["status"], "is_friendly": row["is_friendly"]
        }
        for row in rows
    ]


def update_game_score(game_id, score, *, allow_overwrite=False):
    """Atomically record a score; only administrators may overwrite it."""
    connection = get_connection()

    try:
        connection.execute("SELECT id FROM games WHERE id = %s FOR UPDATE", (game_id,))
        if connection.execute(
            "SELECT 1 FROM game_live_sessions WHERE game_id = %s AND state = 'live'",
            (game_id,),
        ).fetchone():
            raise GameStateConflictError(
                "El partido está en vivo. Usa la captura en vivo para finalizarlo."
            )
        updated_game = connection.execute(
            """
            UPDATE games
            SET
                home_score = %s,
                away_score = %s,
                status = 'completed'
            WHERE id = %s
              AND status <> 'postponed'
              AND (%s OR (
                  status <> 'completed'
                  AND home_score IS NULL
                  AND away_score IS NULL
              ))
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
                game_id,
                allow_overwrite
            )
        ).fetchone()

        if updated_game is None:
            existing = connection.execute(
                "SELECT status, home_score, away_score FROM games WHERE id = %s",
                (game_id,),
            ).fetchone()
            if existing is not None and existing["status"] == "postponed":
                raise GameStateConflictError(
                    "Un partido pospuesto no puede recibir marcador"
                )
            if existing is not None and not allow_overwrite:
                raise GameStateConflictError(
                    "El resultado ya fue registrado. Solo un administrador "
                    "puede modificarlo."
                )

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


def update_game_status(game_id, status):
    """Postpone or restore an unscored game and return its new state."""
    connection = get_connection()
    try:
        connection.execute("SELECT id FROM games WHERE id = %s FOR UPDATE", (game_id,))
        if connection.execute(
            "SELECT 1 FROM game_live_sessions WHERE game_id = %s AND state = 'live'",
            (game_id,),
        ).fetchone():
            raise GameStateConflictError(
                "El partido está en vivo. Usa la captura en vivo para finalizarlo."
            )
        game = connection.execute(
            """
            SELECT id, home_score, away_score
            FROM games
            WHERE id = %s
            FOR UPDATE
            """,
            (game_id,),
        ).fetchone()
        if game is None:
            return None
        if game["home_score"] is not None or game["away_score"] is not None:
            raise GameStateConflictError(
                "Un partido finalizado no puede cambiar de estado"
            )

        updated = connection.execute(
            "UPDATE games SET status = %s WHERE id = %s RETURNING id, status",
            (status, game_id),
        ).fetchone()
        connection.commit()
        return dict(updated)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def delete_game(game_id):
    """Delete one game; database rules clean or detach dependent records."""
    connection = get_connection()
    try:
        deleted = connection.execute(
            "DELETE FROM games WHERE id = %s RETURNING id",
            (game_id,),
        ).fetchone()
        connection.commit()
        return deleted is not None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def delete_games_by_week(week):
    """Delete every game in one jornada as one atomic operation."""
    connection = get_connection()
    try:
        deleted = connection.execute(
            "DELETE FROM games WHERE week = %s RETURNING id",
            (week,),
        ).fetchall()
        connection.commit()
        return len(deleted)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def update_games_status_by_week(week, status):
    """Change every unplayed game in a jornada without altering final results."""
    connection = get_connection()
    try:
        # A concurrent live start must become visible before deciding which
        # games may be postponed; serialize the bulk operation with capture.
        connection.execute("LOCK TABLE games IN EXCLUSIVE MODE")
        existing = connection.execute(
            "SELECT COUNT(*) AS total FROM games WHERE week = %s",
            (week,),
        ).fetchone()["total"]
        if existing == 0:
            return None

        updated = connection.execute(
            """
            UPDATE games
            SET status = %s
            WHERE week = %s
              AND home_score IS NULL
              AND away_score IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM game_live_sessions live
                  WHERE live.game_id = games.id AND live.state = 'live'
              )
            RETURNING id
            """,
            (status, week),
        ).fetchall()
        connection.commit()
        return len(updated)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def assign_referee(game_id, user_id, position, assigned_by):
    """Assign an official to one named slot, replacing that slot atomically."""
    connection = get_connection()
    try:
        # A role sheet has one person per position. Reassigning a position is
        # intentional and should not leave the previous official attached.
        connection.execute(
            "DELETE FROM game_referees WHERE game_id = %s AND position = %s",
            (game_id, position)
        )
        row = connection.execute(
            """
            INSERT INTO game_referees (game_id, user_id, position, assigned_by)
            VALUES (%s, %s, %s, %s)
            RETURNING game_id, user_id, position, assigned_by, assigned_at
            """,
            (game_id, user_id, position, assigned_by)
        ).fetchone()
        connection.commit()
        return dict(row)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_game_referee(game_id, user_id):
    """Return one referee assignment, or None."""
    connection = get_connection()
    row = connection.execute(
        """
        SELECT game_id, user_id, position, assigned_by, assigned_at
        FROM game_referees WHERE game_id = %s AND user_id = %s
        """,
        (game_id, user_id)
    ).fetchone()
    connection.close()
    return dict(row) if row is not None else None


def remove_referee(game_id, user_id):
    """Remove an assignment while leaving the game intact."""
    connection = get_connection()
    deleted = connection.execute(
        "DELETE FROM game_referees WHERE game_id = %s AND user_id = %s RETURNING 1",
        (game_id, user_id)
    ).fetchone()
    connection.commit()
    connection.close()
    return deleted is not None


def get_game_referees(game_id):
    """List assigned referees for league administration."""
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT users.id, users.name, users.email, players.aka,
               COALESCE(NULLIF(players.aka, ''), users.name) AS display_name,
               game_referees.position, game_referees.assigned_at,
               game_referees.assigned_by
        FROM game_referees
        JOIN users ON users.id = game_referees.user_id
        LEFT JOIN players ON players.id = users.player_id
        WHERE game_referees.game_id = %s
        ORDER BY CASE game_referees.position
            WHEN 'referee' THEN 1 WHEN 'down_judge' THEN 2
            WHEN 'field_judge' THEN 3 WHEN 'side_judge' THEN 4
            WHEN 'statistician' THEN 5 END
        """,
        (game_id,)
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def get_games_for_referee(user_id):
    """Return assigned games with the complete crew for each visible game."""
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT
            games.id,
            games.home_score,
            games.away_score,
            games.week,
            games.field_number,
            games.start_time,
            games.status,
            games.is_friendly,
            game_referees.position AS official_position,
            home_team.is_guest AS home_is_guest,
            home_team.id AS home_team_id,
            home_team.name AS home_team_name,
            home_team.branch AS home_team_branch,
            home_team.category AS home_team_category,
            home_team.logo_version AS home_team_has_logo,
            away_team.is_guest AS away_is_guest,
            away_team.id AS away_team_id,
            away_team.name AS away_team_name,
            away_team.branch AS away_team_branch,
            away_team.category AS away_team_category,
            away_team.logo_version AS away_team_has_logo
        FROM game_referees
        JOIN games ON games.id = game_referees.game_id
        JOIN teams AS home_team ON home_team.id = games.home_team_id
        JOIN teams AS away_team ON away_team.id = games.away_team_id
        WHERE game_referees.user_id = %s
        ORDER BY games.week, games.id
        """,
        (user_id,)
    ).fetchall()
    game_ids = [row["id"] for row in rows]
    crew_by_game = {game_id: [] for game_id in game_ids}
    if game_ids:
        crew_rows = connection.execute(
            """
            SELECT game_referees.game_id, game_referees.position,
                   users.id AS user_id,
                   COALESCE(NULLIF(players.aka, ''), users.name) AS display_name,
                   CASE
                       WHEN players.profile_photo_path IS NOT NULL
                           THEN '/media/profiles/' || players.profile_photo_path
                       WHEN users.profile_photo_path IS NOT NULL
                           THEN '/media/profiles/' || users.profile_photo_path
                       ELSE NULL
                   END AS profile_photo_url
            FROM game_referees
            JOIN users ON users.id = game_referees.user_id
            LEFT JOIN players ON players.id = users.player_id
            WHERE game_referees.game_id = ANY(%s)
            ORDER BY game_referees.game_id,
                CASE game_referees.position
                    WHEN 'referee' THEN 1
                    WHEN 'down_judge' THEN 2
                    WHEN 'field_judge' THEN 3
                    WHEN 'side_judge' THEN 4
                    WHEN 'statistician' THEN 5
                    ELSE 6
                END
            """,
            (game_ids,)
        ).fetchall()
        for official in crew_rows:
            crew_by_game[official["game_id"]].append({
                "user_id": official["user_id"],
                "display_name": official["display_name"],
                "position": official["position"],
                "profile_photo_url": official["profile_photo_url"],
            })
    connection.close()
    return [
        {
            "id": row["id"],
            "home_team": {
                "id": row["home_team_id"], "is_guest": row["home_is_guest"],
                "name": row["home_team_name"],
                "branch": row["home_team_branch"],
                "category": row["home_team_category"],
                **(
                    {"logo_url": f"/api/teams/{row['home_team_id']}/logo?v={row['home_team_has_logo']}&size=256"}
                    if row["home_team_has_logo"] else {}
                )
            },
            "away_team": {
                "id": row["away_team_id"], "is_guest": row["away_is_guest"],
                "name": row["away_team_name"],
                "branch": row["away_team_branch"],
                "category": row["away_team_category"],
                **(
                    {"logo_url": f"/api/teams/{row['away_team_id']}/logo?v={row['away_team_has_logo']}&size=256"}
                    if row["away_team_has_logo"] else {}
                )
            },
            "home_score": row["home_score"],
            "away_score": row["away_score"],
            "week": row["week"],
            "field_number": row["field_number"],
            "start_time": row["start_time"],
            "status": row["status"], "is_friendly": row["is_friendly"],
            "official_position": row["official_position"],
            "officials": crew_by_game[row["id"]]
        }
        for row in rows
    ]


def apply_referee_schedule(assignments, assigned_by):
    """Idempotently apply reviewed referee assignments by game and position."""
    connection = get_connection()
    created = 0
    updated = 0
    skipped = 0

    try:
        connection.execute("LOCK TABLE game_referees IN SHARE ROW EXCLUSIVE MODE")

        for assignment in assignments:
            game = connection.execute(
                """
                SELECT id, field_number, start_time
                FROM games
                WHERE id = %s
                FOR UPDATE
                """,
                (assignment.game_id,)
            ).fetchone()
            if game is None:
                raise ValueError(f"No existe el partido {assignment.game_id}")

            desired_time = assignment.scheduled_time or game["start_time"]
            if (
                game["field_number"] != assignment.field_number
                or game["start_time"] != desired_time
            ):
                connection.execute(
                    """
                    UPDATE games
                    SET field_number = %s,
                        start_time = %s
                    WHERE id = %s
                    """,
                    (
                        assignment.field_number,
                        desired_time,
                        assignment.game_id,
                    )
                )

            for official in assignment.officials:
                current_position = connection.execute(
                    """
                    SELECT user_id
                    FROM game_referees
                    WHERE game_id = %s AND position = %s
                    """,
                    (assignment.game_id, official.position)
                ).fetchone()

                if (
                    current_position is not None
                    and current_position["user_id"] == official.user_id
                ):
                    skipped += 1
                    continue

                connection.execute(
                    """
                    DELETE FROM game_referees
                    WHERE game_id = %s
                      AND user_id = %s
                      AND position <> %s
                    """,
                    (
                        assignment.game_id,
                        official.user_id,
                        official.position,
                    )
                )

                if current_position is None:
                    connection.execute(
                        """
                        INSERT INTO game_referees
                            (game_id, user_id, position, assigned_by)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            assignment.game_id,
                            official.user_id,
                            official.position,
                            assigned_by,
                        )
                    )
                    created += 1
                else:
                    connection.execute(
                        """
                        UPDATE game_referees
                        SET user_id = %s,
                            assigned_by = %s,
                            assigned_at = CURRENT_TIMESTAMP
                        WHERE game_id = %s AND position = %s
                        """,
                        (
                            official.user_id,
                            assigned_by,
                            assignment.game_id,
                            official.position,
                        )
                    )
                    updated += 1

        connection.commit()
        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
