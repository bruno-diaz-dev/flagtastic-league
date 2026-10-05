"""Atomic, auditable live-game persistence and final statistics publication."""

from database import get_connection
from services.live_game import METRICS, project_events


class LiveGameError(ValueError):
    """An expected state, roster, or optimistic concurrency conflict."""
    def __init__(self, message, status_code=409):
        super().__init__(message)
        self.status_code = status_code


def locked_game(connection, game_id):
    game = connection.execute("SELECT * FROM games WHERE id = %s FOR UPDATE", (game_id,)).fetchone()
    if game is None:
        raise LiveGameError("Partido no encontrado", 404)
    return game


def session_for(connection, game_id):
    return connection.execute("SELECT * FROM game_live_sessions WHERE game_id = %s", (game_id,)).fetchone()


def require_live(game, session):
    if session is None or session["state"] != "live" or game["status"] != "scheduled":
        raise LiveGameError("La captura solo está disponible mientras el partido está en vivo")
    if game["home_score"] is not None or game["away_score"] is not None:
        raise LiveGameError("El resultado ya fue registrado")


def events_for(connection, game_id):
    return connection.execute("SELECT * FROM game_live_events WHERE game_id = %s ORDER BY id", (game_id,)).fetchall()


def roster_for(connection, game):
    return connection.execute("""
        SELECT tp.team_id, tp.player_id, tp.jersey_number,
               COALESCE(NULLIF(p.aka, ''), p.name) AS display_name
        FROM team_players tp JOIN players p ON p.id = tp.player_id
        WHERE tp.team_id IN (%s, %s)
        ORDER BY tp.team_id, tp.jersey_number, p.name
    """, (game["home_team_id"], game["away_team_id"])).fetchall()


def attendance_for(connection, game, roster):
    """Explicit check-ins, deduplicated by match; never infer from statistics."""
    rows = connection.execute("""
        SELECT e.team_id, e.player_id,
               COUNT(DISTINCT e.game_id) FILTER (WHERE g.status = 'completed') AS attended,
               BOOL_OR(e.game_id = %s) AS present,
               MAX(e.id) FILTER (WHERE e.game_id = %s) AS entry_id
        FROM game_live_events e JOIN games g ON g.id = e.game_id
        WHERE e.kind = 'attendance' AND e.voided_at IS NULL
          AND e.team_id IN (%s, %s)
        GROUP BY e.team_id, e.player_id
    """, (game['id'], game['id'], game['home_team_id'], game['away_team_id'])).fetchall()
    records = {(r['team_id'], r['player_id']): r for r in rows}
    scheduled = connection.execute("""
        SELECT team_id, COUNT(*) AS total FROM (
            SELECT home_team_id AS team_id FROM games WHERE home_team_id IN (%s, %s)
            UNION ALL
            SELECT away_team_id AS team_id FROM games WHERE away_team_id IN (%s, %s)
        ) calendar GROUP BY team_id
    """, (game['home_team_id'], game['away_team_id']) * 2).fetchall()
    totals = {r['team_id']: r['total'] for r in scheduled}
    result = []
    for player in roster:
        record = records.get((player['team_id'], player['player_id']), {})
        total = totals.get(player['team_id'], 0)
        required = total // 2 + 1 if total else None
        attended = record.get('attended', 0)
        result.append({**dict(player), 'present': record.get('present', False),
                       'entry_id': record.get('entry_id'), 'attended_games': attended,
                       'scheduled_games': total, 'required_games': required,
                       'eligible': required is not None and attended >= required})
    return result


def read_live_game(game_id):
    """Read a consistent projection without exposing identifiers or staff IDs."""
    with get_connection() as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        game = connection.execute("""
            SELECT g.*, h.name AS home_name, a.name AS away_name
            FROM games g JOIN teams h ON h.id = g.home_team_id
            JOIN teams a ON a.id = g.away_team_id WHERE g.id = %s
        """, (game_id,)).fetchone()
        if game is None:
            raise LiveGameError("Partido no encontrado", 404)
        session = session_for(connection, game_id)
        events = events_for(connection, game_id)
        scores, totals = project_events(events, game["home_team_id"], game["away_team_id"])
        rosters = roster_for(connection, game)
        identities = {(p["team_id"], p["player_id"]): p for p in rosters}
        for row in totals:
            identity = identities.get((row["team_id"], row["player_id"]), {})
            row.update(display_name=identity.get("display_name", "Jugador"), jersey_number=identity.get("jersey_number"))
        public_events = [{key: row[key] for key in (
            "id", "kind", "team_id", "player_id", "receiver_id", "player_label", "receiver_label",
            "period", "minute", "second", "note", "created_at", "voided_at",
        )} for row in events if row["kind"] != "attendance"]
        state = session["state"] if session else "not_started"
        if game["status"] == "completed":
            state = "completed"
        elif game["status"] == "postponed":
            state = "postponed"
        return {
            "game_id": game_id, "state": state,
            "version": session["version"] if session else 0,
            "started_at": session["started_at"] if session else None,
            "finished_at": session["finished_at"] if session else None,
            "week": game["week"],
            "home_team": {"id": game["home_team_id"], "name": game["home_name"]},
            "away_team": {"id": game["away_team_id"], "name": game["away_name"]},
            "home_score": game["home_score"] if state == "completed" else scores[game["home_team_id"]],
            "away_score": game["away_score"] if state == "completed" else scores[game["away_team_id"]],
            "attendance": attendance_for(connection, game, rosters),
            "events": public_events, "statistics": totals, "roster": [dict(p) for p in rosters],
        }


def start_live_game(game_id, user_id):
    with get_connection() as connection:
        connection.execute("LOCK TABLE games IN ROW EXCLUSIVE MODE")
        game = locked_game(connection, game_id)
        if game["status"] != "scheduled" or game["home_score"] is not None or game["away_score"] is not None:
            raise LiveGameError("Solo puedes iniciar un partido pendiente sin resultado")
        if session_for(connection, game_id) is None:
            if connection.execute("SELECT 1 FROM player_week_stats WHERE game_id = %s LIMIT 1", (game_id,)).fetchone():
                raise LiveGameError("El partido ya tiene estadísticas importadas")
            # Acquire the write lock also used by legacy schedule/stat imports.
            connection.execute("UPDATE games SET status = status WHERE id = %s", (game_id,))
            connection.execute("INSERT INTO game_live_sessions (game_id, started_by) VALUES (%s, %s)", (game_id, user_id))
    return {"state": "live"}


def append_event(game_id, payload, user_id):
    with get_connection() as connection:
        game = locked_game(connection, game_id)
        existing = connection.execute("SELECT * FROM game_live_events WHERE game_id = %s AND client_id = %s", (game_id, payload["client_id"])).fetchone()
        if existing:
            if any(existing[key] != payload[key] for key in ("kind", "team_id", "player_id", "receiver_id", "period", "minute", "second", "note")):
                raise LiveGameError("La clave de la jugada ya fue utilizada para otro contenido")
            return {"id": existing["id"], "duplicate": True}
        require_live(game, session_for(connection, game_id))
        if payload["kind"] not in ("halftime", "two_minute_warning") and payload["team_id"] not in (game["home_team_id"], game["away_team_id"]):
            raise LiveGameError("El equipo no pertenece a este partido", 422)
        roster = {p["player_id"]: p for p in roster_for(connection, game) if p["team_id"] == payload["team_id"]}
        for key in ("player_id", "receiver_id"):
            if payload[key] is not None and payload[key] not in roster:
                raise LiveGameError("El jugador no pertenece al equipo seleccionado", 422)
        def label(key):
            p = roster.get(payload[key])
            return f"#{p['jersey_number']} {p['display_name']}" if p else None
        saved = connection.execute("""
            INSERT INTO game_live_events (game_id, client_id, kind, team_id, player_id, receiver_id,
                player_label, receiver_label, period, minute, second, note, recorded_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (game_id, payload["client_id"], payload["kind"], payload["team_id"], payload["player_id"], payload["receiver_id"], label("player_id"), label("receiver_id"), payload["period"], payload["minute"], payload["second"], payload["note"], user_id)).fetchone()
        connection.execute("UPDATE game_live_sessions SET version = version + 1 WHERE game_id = %s", (game_id,))
        return {"id": saved["id"], "duplicate": False}


def publish(connection, game):
    """Replace only this game's totals and result in the same transaction."""
    scores, totals = project_events(events_for(connection, game["id"]), game["home_team_id"], game["away_team_id"])
    if scores[game["home_team_id"]] == scores[game["away_team_id"]]:
        raise LiveGameError("La liga no admite empates. Revisa las anotaciones antes de finalizar")
    connection.execute("DELETE FROM player_week_stats WHERE game_id = %s", (game["id"],))
    for player in totals:
        connection.execute("""
            INSERT INTO player_week_stats (week, game_id, player_id, team_id, points, receptions,
                interceptions, sacks, tackles, passes_completed, passes_attempted)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (game["week"], game["id"], player["player_id"], player["team_id"], *(player[key] for key in METRICS)))
    connection.execute("UPDATE games SET home_score = %s, away_score = %s, status = 'completed' WHERE id = %s", (scores[game["home_team_id"]], scores[game["away_team_id"]], game["id"]))


def finish_live_game(game_id, expected_version, user_id):
    with get_connection() as connection:
        game = locked_game(connection, game_id)
        session = session_for(connection, game_id)
        if session and session["state"] == "completed":
            return {"state": "completed"}
        require_live(game, session)
        if session["version"] != expected_version:
            raise LiveGameError("Hay nuevas jugadas. Actualiza y revisa el marcador antes de finalizar")
        publish(connection, game)
        connection.execute("UPDATE game_live_sessions SET state = 'completed', finished_at = NOW(), finished_by = %s, version = version + 1 WHERE game_id = %s", (user_id, game_id))
        return {"state": "completed"}


def void_event(game_id, event_id, payload, user_id, is_admin, is_referee):
    with get_connection() as connection:
        game = locked_game(connection, game_id)
        session = session_for(connection, game_id)
        if session is None:
            raise LiveGameError("El partido no tiene captura en vivo")
        if session["state"] == "completed":
            if not is_admin:
                raise LiveGameError("Solo un administrador puede corregir un partido finalizado", 403)
        else:
            if not is_referee:
                raise LiveGameError("Solo árbitros pueden corregir la captura en vivo", 403)
            require_live(game, session)
        if session["version"] != payload["expected_version"]:
            raise LiveGameError("Hay nuevas jugadas. Actualiza antes de corregir")
        event = connection.execute("SELECT id, voided_at, kind, team_id, player_id FROM game_live_events WHERE game_id = %s AND id = %s", (game_id, event_id)).fetchone()
        if event is None:
            raise LiveGameError("Jugada no encontrada", 404)
        if event["voided_at"] is None:
            connection.execute("UPDATE game_live_events SET voided_at = NOW(), voided_by = %s, void_reason = %s WHERE id = %s", (user_id, payload["reason"].strip(), event_id))
            if event["kind"] == "attendance":
                connection.execute("UPDATE game_live_events SET voided_at=NOW(), voided_by=%s, void_reason=%s WHERE game_id=%s AND team_id=%s AND player_id=%s AND kind='attendance' AND voided_at IS NULL", (user_id, payload["reason"].strip(), game_id, event["team_id"], event["player_id"]))
            if session["state"] == "completed":
                publish(connection, game)
            connection.execute("UPDATE game_live_sessions SET version = version + 1 WHERE game_id = %s", (game_id,))
        return {"voided": True}
