"""Resolve pre-created playoff games once both feeder games have final scores."""


class BracketConflictError(ValueError):
    """A corrected semifinal would change a final that already started."""


def _target_started(connection, game_id):
    """A playoff game is locked once it has a result, stats or a capture."""
    return connection.execute("""
        SELECT EXISTS (
            SELECT 1 FROM games
            WHERE id=%s AND (status='completed' OR home_score IS NOT NULL
                             OR away_score IS NOT NULL)
            UNION ALL SELECT 1 FROM game_live_sessions WHERE game_id=%s
            UNION ALL SELECT 1 FROM player_week_stats WHERE game_id=%s
        ) AS started
    """, (game_id, game_id, game_id)).fetchone()["started"]


def resolve_completed_bracket_slots(connection, source_game_id):
    """Fill or correct the final/third-place teams fed by this game.

    A corrected semifinal score replaces the teams of a playoff game that has
    not started. If it has a result, statistics or a capture, the correction
    is rejected so an administrator decides instead of silently diverging.
    """
    slots = connection.execute("""
        SELECT * FROM game_bracket_slots
        WHERE target_game_id IS NOT NULL
          AND (source_game_id=%s OR opponent_game_id=%s)
        ORDER BY id FOR UPDATE
    """, (source_game_id, source_game_id)).fetchall()
    updated = []
    for slot in slots:
        feeders = connection.execute("""
            SELECT id, home_team_id, away_team_id, home_score, away_score, status
            FROM games WHERE id IN (%s,%s) ORDER BY field_number,id
        """, (slot["source_game_id"], slot["opponent_game_id"])).fetchall()
        if len(feeders) != 2 or any(
            game["status"] != "completed" or game["home_score"] is None
            or game["away_score"] is None or game["home_score"] == game["away_score"]
            for game in feeders
        ):
            continue
        teams = []
        for game in feeders:
            home_won = game["home_score"] > game["away_score"]
            winner = game["home_team_id"] if home_won else game["away_team_id"]
            loser = game["away_team_id"] if home_won else game["home_team_id"]
            teams.append(winner if slot["placement"] == "final" else loser)
        target = connection.execute(
            "SELECT id, home_team_id, away_team_id FROM games WHERE id=%s FOR UPDATE",
            (slot["target_game_id"],),
        ).fetchone()
        if target is None:
            continue
        current = (target["home_team_id"], target["away_team_id"])
        if current == tuple(teams):
            continue
        if current != (None, None) and _target_started(connection, target["id"]):
            raise BracketConflictError(
                f"{slot['label']} ya tiene captura, estadísticas o resultado con "
                "los equipos anteriores. Corrígelo manualmente antes de cambiar "
                "el marcador de la semifinal."
            )
        result = connection.execute("""
            UPDATE games
            SET home_team_id=%s, away_team_id=%s,
                home_pending_label=NULL, away_pending_label=NULL
            WHERE id=%s
            RETURNING id
        """, (teams[0], teams[1], target["id"])).fetchone()
        if result:
            updated.append(result["id"])
    return updated
