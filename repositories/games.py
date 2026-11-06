"""Persistence operations for games and final scores."""

from database import get_connection
from collections import Counter
from services.schedule_context import venue_key


class ScheduleConflictError(ValueError):
    """A schedule replacement would discard or misattribute existing data."""


class GameStateConflictError(ValueError):
    """The requested transition conflicts with the current game state."""


class CalendarMigrationRequired(ScheduleConflictError, GameStateConflictError):
    """Calendar writes must not silently drop metadata on an older database."""


UNSET = object()
CALENDAR_COLUMNS = "(to_jsonb(games)->>'game_date')::date AS game_date, to_jsonb(games)->>'venue' AS venue"


def calendar_available(connection):
    return connection.execute("""
        SELECT COUNT(*) AS n FROM information_schema.columns
        WHERE table_schema='public' AND table_name='games' AND column_name IN ('game_date','venue')
    """).fetchone()["n"] == 2


def require_calendar(connection):
    if not calendar_available(connection):
        raise CalendarMigrationRequired("Falta activar fecha y sede en Supabase. Aplica la migración del calendario antes de guardar estos datos")


def get_calendar_capabilities():
    """Expose a feature flag, never schema contents or credentials."""
    with get_connection() as connection:
        return {"date_and_venue": calendar_available(connection)}


def calendar_slot_rows(connection, week, field_number, start_time, exclude=None):
    return connection.execute(f"""
        SELECT games.*, {CALENDAR_COLUMNS} FROM games
        WHERE week=%s AND field_number IS NOT DISTINCT FROM %s
          AND start_time IS NOT DISTINCT FROM %s AND id IS DISTINCT FROM %s
        ORDER BY id FOR UPDATE
    """, (week, field_number, start_time, exclude)).fetchall()


def same_calendar(row, game_date, venue):
    return row.get("game_date") == game_date and venue_key(row.get("venue")) == venue_key(venue)


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
    if (len(known) == 2 and not game.is_friendly
            and not teams_share_game_division(known["home"], known["away"])):
        raise ScheduleConflictError("Los equipos deben pertenecer a la misma rama y categoria; U8, U10 y U12 permiten cruces entre ramas")
    reference = next(iter(known.values()), None)
    branch = (game.branch if game.is_friendly and game.branch else
              reference["branch"] if reference else game.branch)
    category = (game.category if game.is_friendly and game.category else
                reference["category"] if reference else game.category)
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
    """Create a fixture and its invited teams, preserving calendar context."""
    with get_connection() as connection:
        connection.execute("LOCK TABLE games IN SHARE ROW EXCLUSIVE MODE")
        if game.game_date is not None or game.venue is not None:
            require_calendar(connection)
        game = resolve_game_participants(connection, game)
        if game.start_time is not None and any(same_calendar(row, game.game_date, game.venue)
                for row in calendar_slot_rows(connection, game.week, game.field_number, game.start_time)):
            raise ScheduleConflictError("Ese campo ya tiene un partido en la misma fecha, sede y hora")
        columns = "home_team_id, away_team_id, week, field_number, start_time, is_friendly"
        values = [game.home_team_id, game.away_team_id, game.week, game.field_number, game.start_time, game.is_friendly]
        if game.game_date is not None or game.venue is not None:
            columns += ", game_date, venue"
            values.extend([game.game_date, game.venue])
        row = connection.execute(
            f"INSERT INTO games ({columns}) VALUES ({','.join(['%s'] * len(values))}) "
            f"RETURNING id, home_team_id, away_team_id, week, field_number, start_time, status, is_friendly, {CALENDAR_COLUMNS}",
            values,
        ).fetchone()
        return dict(row)


def import_game_schedule(games):
    """Upsert reviewed slots, distinguishing calendar day and venue."""
    with get_connection() as connection:
        connection.execute("LOCK TABLE games IN SHARE ROW EXCLUSIVE MODE")
        has_calendar = calendar_available(connection)
        if not has_calendar and any(game.game_date is not None or game.venue is not None for game in games):
            require_calendar(connection)
        slot_counts = Counter((game.week, game.field_number, game.start_time) for game in games)
        created = updated = skipped = 0
        for game in games:
            game = resolve_game_participants(connection, game)
            rows = calendar_slot_rows(connection, game.week, game.field_number, game.start_time)
            exact = [row for row in rows
                     if (game.game_date is None or row.get('game_date') == game.game_date)
                     and (game.venue is None or venue_key(row.get('venue')) == venue_key(game.venue))]
            if len(exact) > 1:
                raise ScheduleConflictError("Hay varios partidos en ese horario y campo. Indica fecha y sede para identificar el correcto")
            existing = exact[0] if exact else None
            if existing is None:
                legacy = [row for row in rows
                          if (row.get('game_date') is None or game.game_date is None or row['game_date'] == game.game_date)
                          and (not row.get('venue') or game.venue is None or venue_key(row['venue']) == venue_key(game.venue))]
                if legacy:
                    if (len(legacy) != 1 or slot_counts[(game.week, game.field_number, game.start_time)] != 1
                            or legacy[0]['home_team_id'] != game.home_team_id or legacy[0]['away_team_id'] != game.away_team_id):
                        raise ScheduleConflictError("Hay un partido sin fecha o sede en ese espacio. Completa su calendario antes de reemplazarlo")
                    existing = legacy[0]
            if existing is not None:
                desired_date = game.game_date if game.game_date is not None else existing.get('game_date')
                desired_venue = game.venue if game.venue is not None else existing.get('venue')
                same_teams = (existing['home_team_id'] == game.home_team_id and existing['away_team_id'] == game.away_team_id
                              and existing['is_friendly'] == game.is_friendly)
                metadata_changed = not same_calendar(existing, desired_date, desired_venue)
                if same_teams and not metadata_changed:
                    skipped += 1
                    continue
                if (existing['status'] == 'completed' or existing['home_score'] is not None or existing['away_score'] is not None):
                    raise ScheduleConflictError(f"El partido {existing['id']} ya tiene resultados; no se puede reemplazar ni cambiar su calendario")
                if not same_teams:
                    related = connection.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM player_week_stats WHERE game_id=%s
                            UNION ALL SELECT 1 FROM game_live_events WHERE game_id=%s
                            UNION ALL SELECT 1 FROM game_live_sessions WHERE game_id=%s
                        ) AS present
                    """, (existing['id'],) * 3).fetchone()['present']
                    if related:
                        raise ScheduleConflictError(f"El partido {existing['id']} ya tiene estadísticas o captura registrada. No se pueden reemplazar sus equipos")
                metadata_sql = ", game_date=%s, venue=%s" if has_calendar else ""
                args = [game.home_team_id, game.away_team_id, game.is_friendly]
                if has_calendar:
                    args.extend([desired_date, desired_venue])
                connection.execute("UPDATE games SET home_team_id=%s, away_team_id=%s, is_friendly=%s" + metadata_sql + " WHERE id=%s", [*args, existing['id']])
                updated += 1
                continue
            columns = "home_team_id, away_team_id, week, field_number, start_time, is_friendly"
            args = [game.home_team_id, game.away_team_id, game.week, game.field_number, game.start_time, game.is_friendly]
            if has_calendar:
                columns += ", game_date, venue"
                args.extend([game.game_date, game.venue])
            connection.execute(f"INSERT INTO games ({columns}) VALUES ({','.join(['%s'] * len(args))})", args)
            created += 1
        return {"created": created, "updated": updated, "skipped": skipped}

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
            (to_jsonb(games)->>'game_date')::date AS game_date,
            to_jsonb(games)->>'venue' AS venue,
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
                "id": row["home_team_id"], **({"is_guest": True} if row["home_is_guest"] else {}),
                "name": row["home_team_name"],
                "branch": row["home_team_branch"],
                "category": row["home_team_category"],
                **(
                    {"logo_url": f"/api/teams/{row['home_team_id']}/logo?v={row['home_team_has_logo']}&size=256"}
                    if row["home_team_has_logo"] else {}
                )
            },

            "away_team": {
                "id": row["away_team_id"], **({"is_guest": True} if row["away_is_guest"] else {}),
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
            "start_time": row["start_time"], "game_date": row["game_date"], "venue": row["venue"],
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


def update_game_schedule(game_id, start_time, field_number=None, *, game_date=UNSET, venue=UNSET):
    """Move a fixture in place across days/venues without changing its ID or crew."""
    with get_connection() as connection:
        connection.execute("LOCK TABLE games IN EXCLUSIVE MODE")
        game = connection.execute(f"SELECT games.*, {CALENDAR_COLUMNS} FROM games WHERE id=%s FOR UPDATE", (game_id,)).fetchone()
        if game is None:
            return None
        if game['status'] == 'completed' or game['home_score'] is not None or game['away_score'] is not None:
            raise GameStateConflictError("No se puede cambiar el calendario de un partido finalizado")
        desired_field = field_number if field_number is not None else game['field_number']
        desired_date = game.get('game_date') if game_date is UNSET else game_date
        desired_venue = game.get('venue') if venue is UNSET else venue
        metadata_changed = not same_calendar(game, desired_date, desired_venue)
        if metadata_changed:
            require_calendar(connection)
        changed = metadata_changed or game['start_time'] != start_time or game['field_number'] != desired_field
        if changed and any(same_calendar(row, desired_date, desired_venue)
                           for row in calendar_slot_rows(connection, game['week'], desired_field, start_time, game_id)):
            raise GameStateConflictError("Ese campo ya tiene otro partido en la misma jornada, fecha, sede y hora")
        metadata_sql = ", game_date=%s, venue=%s" if metadata_changed else ""
        args = [start_time, desired_field]
        if metadata_changed:
            args.extend([desired_date, desired_venue])
        updated = connection.execute("UPDATE games SET start_time=%s, field_number=%s" + metadata_sql
            + f" WHERE id=%s RETURNING id, week, field_number, start_time, status, {CALENDAR_COLUMNS}", [*args, game_id]).fetchone()
        return dict(updated)


def update_game_status(game_id, status):
    """Postpone or restore an unscored game and return its new state."""
    connection = get_connection()
    try:
        connection.execute("SELECT id FROM games WHERE id = %s FOR UPDATE", (game_id,))
        game = connection.execute(
            """
            SELECT id, status, home_score, away_score
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
        if game["status"] != status:
            connection.execute(
                "UPDATE game_live_sessions SET version = version + 1 WHERE game_id = %s AND state = 'live'",
                (game_id,),
            )
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
    """Change unfinished games, including live capture, without altering results."""
    connection = get_connection()
    try:
        # Serialize postponement/restoration with capture and final publication.
        # Live events remain intact; postponed games reject further writes.
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
              AND status <> %s
            RETURNING id
            """,
            (status, week, status),
        ).fetchall()
        if updated:
            connection.execute(
                "UPDATE game_live_sessions SET version = version + 1 WHERE game_id = ANY(%s) AND state = 'live'",
                ([row["id"] for row in updated],),
            )
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
               COALESCE(NULLIF(users.aka, ''), NULLIF(players.aka, ''), users.name) AS display_name,
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
            (to_jsonb(games)->>'game_date')::date AS game_date,
            to_jsonb(games)->>'venue' AS venue,
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
                   COALESCE(NULLIF(users.aka, ''), NULLIF(players.aka, ''), users.name) AS display_name,
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
                "id": row["home_team_id"], **({"is_guest": True} if row["home_is_guest"] else {}),
                "name": row["home_team_name"],
                "branch": row["home_team_branch"],
                "category": row["home_team_category"],
                **(
                    {"logo_url": f"/api/teams/{row['home_team_id']}/logo?v={row['home_team_has_logo']}&size=256"}
                    if row["home_team_has_logo"] else {}
                )
            },
            "away_team": {
                "id": row["away_team_id"], **({"is_guest": True} if row["away_is_guest"] else {}),
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
            "start_time": row["start_time"], "game_date": row["game_date"], "venue": row["venue"],
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
        connection.execute("LOCK TABLE games IN EXCLUSIVE MODE")
        connection.execute("LOCK TABLE game_referees IN SHARE ROW EXCLUSIVE MODE")
        ids = [assignment.game_id for assignment in assignments]
        if len(ids) != len(set(ids)):
            raise ScheduleConflictError("No se puede confirmar dos veces el mismo partido")
        plans = {}
        for assignment in assignments:
            game = connection.execute(f"SELECT games.*, {CALENDAR_COLUMNS} FROM games WHERE id=%s FOR UPDATE", (assignment.game_id,)).fetchone()
            if game is None:
                raise ValueError(f"No existe el partido {assignment.game_id}")
            positions = {official.position for official in assignment.officials}
            if not game['is_friendly'] and not {'referee', 'down_judge'}.issubset(positions):
                raise ScheduleConflictError("Referee y Down Judge son obligatorios")
            wanted_time = assignment.scheduled_time or game['start_time']
            wanted_date = assignment.game_date if 'game_date' in assignment.model_fields_set else game.get('game_date')
            wanted_venue = assignment.venue if 'venue' in assignment.model_fields_set else game.get('venue')
            changed_meta = not same_calendar(game, wanted_date, wanted_venue)
            changed = changed_meta or game['field_number'] != assignment.field_number or game['start_time'] != wanted_time
            if changed and (game['status'] == 'completed' or game['home_score'] is not None or game['away_score'] is not None):
                raise ScheduleConflictError("No se puede cambiar el calendario de un partido finalizado")
            if changed_meta:
                require_calendar(connection)
            plans[game['id']] = (game, wanted_time, wanted_date, wanted_venue, changed_meta, changed)
        occupied = {}
        for assignment in assignments:
            game, wanted_time, wanted_date, wanted_venue, changed_meta, changed = plans[assignment.game_id]
            if wanted_time is not None:
                key = (game['week'], wanted_date, venue_key(wanted_venue), assignment.field_number, wanted_time)
                if key in occupied and (changed or plans[occupied[key]][5]):
                    raise ScheduleConflictError("Dos partidos ocuparían la misma fecha, sede, campo y hora")
                occupied[key] = game['id']
                if changed and any(row['id'] not in plans and same_calendar(row, wanted_date, wanted_venue)
                        for row in calendar_slot_rows(connection, game['week'], assignment.field_number, wanted_time, game['id'])):
                    raise ScheduleConflictError("Ese campo ya tiene otro partido en la misma fecha, sede y hora")
        for assignment in assignments:
            game, desired_time, desired_date, desired_venue, changed_meta, changed = plans[assignment.game_id]
            if changed:
                sql_meta = ', game_date=%s, venue=%s' if changed_meta else ''
                args = [assignment.field_number, desired_time]
                if changed_meta:
                    args.extend([desired_date, desired_venue])
                connection.execute('UPDATE games SET field_number=%s, start_time=%s' + sql_meta + ' WHERE id=%s', [*args, game['id']])

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
