"""Persistence and aggregate queries for weekly player statistics."""

from fractions import Fraction
from uuid import uuid4

from database import get_connection
from services.divisions import (
    category_allows_cross_branch_games,
    normalize_division,
)
from services.team_matching import (
    match_team_name, normalize_team_text, rank_team_matches,
)


class StatisticsValidationError(Exception):
    """Raised when imported statistics conflict with league data."""


def import_statistics_workbook(weeks, games=None, *, link_existing_games_only=False, existing_records="update"):
    """Merge player-game stats; optional stats-only mode keeps games unchanged."""
    if existing_records not in ("preserve", "update"):
        raise StatisticsValidationError("Modo de registros existentes inválido")
    connection = get_connection()
    try:
        # Serialize with live start/finish before replacing any weekly rows.
        connection.execute("LOCK TABLE games IN EXCLUSIVE MODE")
        teams = connection.execute(
            "SELECT id, name, branch, category FROM teams WHERE NOT is_guest"
        ).fetchall()
        teams_by_identity = {
            (*normalize_division(team["branch"], team["category"]),
             normalize_team_text(team["name"])): team
            for team in teams
        }

        def resolve_team(label, branch, category):
            division = normalize_division(branch, category)
            team_name = normalize_team_text(label)
            exact = teams_by_identity.get((*division, team_name))
            if exact:
                return exact
            return match_team_name(
                label,
                teams,
                branch=(
                    None
                    if category_allows_cross_branch_games(division[1])
                    else division[0]
                ),
                category=division[1]
            )
        # An official game pair is stronger evidence than the branch assumed
        # from an unqualified Excel label ("U12" defaults to "mixto").
        # Resolve both opponents against registered matches for that week;
        # this disambiguates homonymous cross-branch youth teams such as the
        # two U12 Nómadas, without changing either team or the Excel.
        recorded_game_pairs = {}
        recorded_game_ids = {}
        recorded_game_home_ids = {}
        unresolved_game_indices = {}
        if games:
            teams_by_id = {team["id"]: team for team in teams}
            registered_games = connection.execute(
                """
                SELECT id, week, home_team_id, away_team_id, status, home_score, away_score
                FROM games
                WHERE week = ANY(%s) AND NOT is_friendly
                ORDER BY id
                """,
                (list(games),),
            ).fetchall()
            claimed_games = set()
            for week, source_games in games.items():
                for fallback_index, source_game in enumerate(source_games):
                    game_index = source_game.get("game_index", fallback_index)
                    category = source_game["category"]
                    branch = (
                        None if category_allows_cross_branch_games(category)
                        else source_game["branch"]
                    )
                    candidates = []
                    for official_game in registered_games:
                        if (official_game["week"] != week
                                or official_game["id"] in claimed_games
                                or official_game["home_team_id"] not in teams_by_id
                                or official_game["away_team_id"] not in teams_by_id):
                            continue
                        participants = [
                            teams_by_id[official_game["home_team_id"]],
                            teams_by_id[official_game["away_team_id"]],
                        ]
                        home = match_team_name(
                            source_game["home_team"], participants,
                            branch=branch, category=category,
                        )
                        away = match_team_name(
                            source_game["away_team"], participants,
                            branch=branch, category=category,
                        )
                        if home and away and home["id"] != away["id"]:
                            candidates.append((official_game, home, away))
                    if not candidates:
                        if not link_existing_games_only:
                            continue
                        unresolved_game_indices.setdefault(week, set()).add(game_index)
                        continue
                    distinct_pairs = {
                        tuple(sorted((home["id"], away["id"])))
                        for _, home, away in candidates
                    }
                    if len(distinct_pairs) > 1 and not link_existing_games_only:
                        # Shared youth names can have the same opponent in two
                        # branches. Use only an exact published score match;
                        # otherwise retain the ambiguity error rather than guess.
                        score_matches = []
                        for match, home, away in candidates:
                            if match["status"] != "completed":
                                continue
                            scores = (match["home_score"], match["away_score"])
                            if match["home_team_id"] != home["id"]:
                                scores = scores[::-1]
                            if scores == (source_game["home_score"], source_game["away_score"]):
                                score_matches.append((match, home, away))
                        if score_matches:
                            candidates = score_matches
                            distinct_pairs = {
                                tuple(sorted((home["id"], away["id"])))
                                for _, home, away in candidates
                            }
                    if len(distinct_pairs) > 1:
                        unresolved_game_indices.setdefault(week, set()).add(game_index)
                        continue
                    official_game, home, away = candidates[0]
                    claimed_games.add(official_game["id"])
                    recorded_game_pairs[(week, game_index)] = (home, away)
                    recorded_game_ids[(week, game_index)] = official_game["id"]
                    recorded_game_home_ids[(week, game_index)] = official_game["home_team_id"]

        def resolve_stats_team(row, week):
            game_index = row.get("game_index")
            pair = recorded_game_pairs.get((week, game_index))
            if pair:
                branch = (
                    None if category_allows_cross_branch_games(row["category"])
                    else row["branch"]
                )
                matched = match_team_name(
                    row["team"], pair,
                    branch=branch, category=row["category"],
                )
                if matched:
                    return matched
                return None
            return resolve_team(
                row["team"], row["branch"], row["category"]
            )

        resolved_weeks = {}
        skipped = []

        def skipped_record(week, row, reason, **details):
            record = {
                "week": week, "source_team_name": row["team"],
                "team_name": row["team"], "branch": row["branch"],
                "category": row["category"],
                "jersey_number": row["jersey_number"],
                "game_index": row.get("game_index"), "reason": reason,
                **{field: row.get(field) for field in (
                    "points", "receptions", "interceptions", "sacks",
                    "tackles", "passes_completed", "passes_attempted",
                )},
            }
            record.update(details)
            return record

        preserved_weeks = []
        resolved_candidates = {}
        candidate_team_ids = set()
        candidate_jersey_numbers = set()
        for week, rows in weeks.items():
            resolved_candidates[week] = []
            for row_number, row in enumerate(rows, start=2):
                game_index = row.get("game_index")
                if game_index in unresolved_game_indices.get(week, set()):
                    skipped.append(skipped_record(
                        week, row, "game_unresolved"
                    ))
                    continue
                team = resolve_stats_team(row, week)
                if team is None:
                    possibilities = rank_team_matches(
                        row["team"], teams, row["branch"], row["category"]
                    )
                    suggestions = [
                        candidate["name"] for confidence, candidate
                        in possibilities if confidence >= 0.65
                    ][:3]
                    if game_index is not None:
                        unresolved_game_indices.setdefault(week, set()).add(game_index)
                    skipped.append(skipped_record(
                        week, row, "team_unresolved",
                        candidate_names=suggestions, row_number=row_number,
                    ))
                    continue
                resolved_candidates[week].append((team, row_number, row))
                candidate_team_ids.add(team["id"])
                candidate_jersey_numbers.add(row["jersey_number"])

        players_by_team_jersey = {}
        if candidate_team_ids and candidate_jersey_numbers:
            player_rows = connection.execute(
                """
                SELECT team_players.team_id, team_players.jersey_number,
                       players.id, players.name
                FROM team_players
                JOIN players ON players.id = team_players.player_id
                WHERE team_players.team_id = ANY(%s)
                  AND team_players.jersey_number = ANY(%s)
                """,
                (list(candidate_team_ids), list(candidate_jersey_numbers))
            ).fetchall()
            players_by_team_jersey = {
                (row["team_id"], row["jersey_number"]): row
                for row in player_rows
            }

        for week, candidates in resolved_candidates.items():
            resolved_rows = []
            seen_memberships = set()
            for team, row_number, row in candidates:
                game_index = row.get("game_index")
                if game_index in unresolved_game_indices.get(week, set()):
                    skipped.append(skipped_record(
                        week, row, "game_team_unresolved",
                        team_id=team["id"], team_name=team["name"],
                    ))
                    continue
                player = players_by_team_jersey.get(
                    (team["id"], row["jersey_number"])
                )
                if player is None:
                    skipped.append(skipped_record(
                        week, row, "jersey_number_not_found",
                        team_id=team["id"], team_name=team["name"],
                    ))
                    continue
                membership = (
                    row.get("game_index"), player["id"], team["id"]
                )
                if membership in seen_memberships:
                    raise StatisticsValidationError(
                        f"Jornada {week}, fila {row_number}: jugador repetido"
                    )
                seen_memberships.add(membership)
                resolved_rows.append((player, team, row))
            if rows and not resolved_rows:
                preserved_weeks.append(week)
            else:
                resolved_weeks[week] = resolved_rows

        resolved_games = []
        for week, week_games in (games or {}).items():
            for fallback_index, game in enumerate(week_games):
                game_index = game.get("game_index", fallback_index)
                game = {**game, "game_index": game_index}
                pair = recorded_game_pairs.get((week, game_index))
                if pair:
                    home, away = pair
                else:
                    home = resolve_team(
                        game["home_team"], game["branch"], game["category"]
                    )
                    away = resolve_team(
                        game["away_team"], game["branch"], game["category"]
                    )
                if home is None or away is None:
                    missing = game["home_team"] if home is None else game["away_team"]
                    unresolved_game_indices.setdefault(week, set()).add(game_index)
                    skipped.append({"week": week, "team_name": missing,
                        "branch": game["branch"], "category": game["category"],
                        "game_index": game_index, "reason": "team_unresolved",
                        "candidate_names": []})
                    continue
                # Only import games for divisions with valid statistics.
                # A missing jersey in another division must not alter its games.
                game_division = (
                    home["category"],
                    None if category_allows_cross_branch_games(home["category"])
                    else home["branch"],
                )
                imported_divisions = {
                    (team["category"],
                     None if category_allows_cross_branch_games(team["category"])
                     else team["branch"])
                    for _, team, _ in resolved_weeks.get(week, [])
                }
                if game_division in imported_divisions:
                    resolved_games.append((week, home["id"], away["id"], game))

        for week, blocked_indices in unresolved_game_indices.items():
            if not blocked_indices or week not in resolved_weeks:
                continue
            kept = []
            for player, team, row in resolved_weeks[week]:
                if row.get("game_index") in blocked_indices:
                    skipped.append(skipped_record(
                        week, row, "game_team_unresolved",
                        team_id=team["id"], team_name=team["name"],
                    ))
                else:
                    kept.append((player, team, row))
            resolved_weeks[week] = kept
            if not kept and week not in preserved_weeks:
                preserved_weeks.append(week)

        for week, resolved_rows in resolved_weeks.items():
            team_ids = list({team["id"] for _, team, _ in resolved_rows})
            if team_ids and connection.execute(
                """SELECT 1 FROM game_live_sessions live JOIN games g ON g.id = live.game_id
                WHERE g.week = %s AND (g.home_team_id = ANY(%s) OR g.away_team_id = ANY(%s))
                  AND (live.state = 'live' OR EXISTS (
                      SELECT 1 FROM game_live_events event
                      WHERE event.game_id = live.game_id
                        AND event.kind <> 'attendance'
                        AND event.voided_at IS NULL
                  )) LIMIT 1""",
                (week, team_ids, team_ids),
            ).fetchone():
                raise StatisticsValidationError("Los equipos incluidos tienen captura en vivo en esta jornada. Corrige esos partidos individualmente.")

        # Never delete all statistics for a week or division. A file may
        # contain only one team, or even one player. Reimports update exact
        # player/game snapshots below; other records and weeks stay intact.
        game_ids = {}
        used_existing_game_ids = set()
        for week, home_team_id, away_team_id, game in resolved_games:
            recorded_id = recorded_game_ids.get((week, game["game_index"]))
            if recorded_id is not None:
                existing_candidates = [{"id": recorded_id}]
            elif link_existing_games_only:
                # A statistics upload must link to an existing match without
                # creating games or guessing/overwriting its final score.
                existing_candidates = connection.execute(
                    """
                    SELECT id FROM games
                    WHERE week = %s AND NOT is_friendly
                      AND ((home_team_id = %s AND away_team_id = %s)
                        OR (home_team_id = %s AND away_team_id = %s))
                    ORDER BY id
                    """,
                    (week, home_team_id, away_team_id,
                     away_team_id, home_team_id)
                ).fetchall()
            else:
                existing_candidates = connection.execute(
                    """
                    SELECT id FROM games
                    WHERE week = %s AND home_team_id = %s
                      AND away_team_id = %s AND NOT is_friendly
                    ORDER BY id
                    """,
                    (week, home_team_id, away_team_id)
                ).fetchall()
            existing = next(
                (candidate for candidate in existing_candidates
                 if candidate["id"] not in used_existing_game_ids),
                None
            )
            if existing is None:
                if link_existing_games_only:
                    skipped.append({"week": week, "team_name": game["home_team"],
                        "branch": game["branch"], "category": game["category"],
                        "game_index": game["game_index"],
                        "reason": "game_unresolved", "candidate_names": []})
                    continue
                saved_game = connection.execute(
                    """
                    INSERT INTO games (
                        home_team_id, away_team_id, home_score, away_score,
                        week, status
                    ) VALUES (%s, %s, %s, %s, %s, 'completed')
                    RETURNING id
                    """,
                    (home_team_id, away_team_id, game["home_score"],
                     game["away_score"], week)
                ).fetchone()
            elif link_existing_games_only:
                saved_game = existing
            else:
                # Never overwrite an official completed scoreboard when importing
                # player statistics; the referee/admin result remains authoritative.
                home_score, away_score = game["home_score"], game["away_score"]
                if recorded_game_home_ids.get((week, game["game_index"]), home_team_id) != home_team_id:
                    home_score, away_score = away_score, home_score
                saved_game = connection.execute(
                    """
                    UPDATE games
                    SET home_score = CASE WHEN status = 'completed' THEN home_score ELSE %s END,
                        away_score = CASE WHEN status = 'completed' THEN away_score ELSE %s END,
                        status = 'completed'
                    WHERE id = %s RETURNING id
                    """,
                    (home_score, away_score, existing["id"])
                ).fetchone()
            used_existing_game_ids.add(saved_game["id"])
            game_ids[(week, game["game_index"])] = saved_game["id"]

        existing_stats_by_identity = {}
        stats_weeks = list(resolved_weeks)
        stats_team_ids = list({
            team["id"]
            for rows in resolved_weeks.values()
            for _, team, _ in rows
        })
        stats_player_ids = list({
            player["id"]
            for rows in resolved_weeks.values()
            for player, _, _ in rows
        })
        if stats_weeks and stats_team_ids and stats_player_ids:
            existing_stats = connection.execute(
                """
                SELECT id, week, team_id, player_id, game_id,
                       passes_completed, passes_attempted
                FROM player_week_stats
                WHERE week = ANY(%s)
                  AND team_id = ANY(%s)
                  AND player_id = ANY(%s)
                ORDER BY id FOR UPDATE
                """,
                (stats_weeks, stats_team_ids, stats_player_ids)
            ).fetchall()
            for existing in existing_stats:
                identity = (
                    existing["week"], existing["team_id"],
                    existing["player_id"]
                )
                existing_stats_by_identity.setdefault(identity, []).append(existing)

        imported = []
        updated_count = 0
        retained_count = 0
        pending_inserts = []
        pending_updates = []
        for week, resolved_rows in resolved_weeks.items():
            if not (games or {}).get(week):
                # Official Wk sheets may contain multiple games by one player.
                # Without game mapping these rows cannot be safely identified
                # in the database. Do not silently combine or overwrite them.
                player_counts = {}
                for player, team, row in resolved_rows:
                    key = (player["id"], team["id"])
                    player_counts[key] = player_counts.get(key, 0) + 1
                if any(count > 1 for count in player_counts.values()):
                    raise StatisticsValidationError(
                        f"Jornada {week}: el archivo contiene un jugador en "
                        "varios partidos. Usa Archivo completo con hojas Wk "
                        "para identificar cada encuentro."
                    )
            for player, team, row in resolved_rows:
                game_id = game_ids.get((week, row.get("game_index")))
                matching_stats = existing_stats_by_identity.get(
                    (week, team["id"], player["id"]), []
                )
                existing_rows = (
                    matching_stats if game_id is None else [
                        existing for existing in matching_stats
                        if existing["game_id"] in (None, game_id)
                    ]
                )
                if existing_rows and existing_records == "preserve":
                    retained_count += 1
                    continue
                if len(existing_rows) > 1:
                    raise StatisticsValidationError(
                        f"Jornada {week}, equipo {team['name']}, jugador "
                        f"#{row['jersey_number']}: hay varios partidos "
                        "registrados. Importa el Excel oficial completo "
                        "para evitar mezclar estadísticas."
                    )
                values = (
                    row["points"], row["receptions"], row["interceptions"],
                    row["sacks"], row["tackles"], row["passes_completed"],
                    row["passes_attempted"]
                )
                if existing_rows:
                    if row.get("passing_incomplete"):
                        values = (*values[:5], existing_rows[0]["passes_completed"],
                                  existing_rows[0]["passes_attempted"])
                    pending_updates.append((
                        existing_rows[0]["id"], game_id, values, player, team
                    ))
                    continue
                else:
                    pending_inserts.append((week, game_id, player, team, values))
                    continue
                imported.append({
                    **dict(saved), "player_name": player["name"],
                    "team_name": team["name"], "branch": team["branch"],
                    "category": team["category"]
                })
        update_columns = (
            "id, game_id, points, receptions, interceptions, sacks, tackles, "
            "passes_completed, passes_attempted"
        )
        for offset in range(0, len(pending_updates), 400):
            batch = pending_updates[offset:offset + 400]
            values_sql = ", ".join(
                "(" + ", ".join(["%s"] * 9) + ")" for _ in batch
            )
            parameters = []
            identities = {}
            for row_id, game_id, values, player, team in batch:
                parameters.extend((row_id, game_id, *values))
                identities[row_id] = (player, team)
            saved_rows = connection.execute(
                "UPDATE player_week_stats AS stats "
                "SET game_id = COALESCE(incoming.game_id::integer, stats.game_id), "
                "points = incoming.points, receptions = incoming.receptions, "
                "interceptions = incoming.interceptions, sacks = incoming.sacks, "
                "tackles = incoming.tackles, "
                "passes_completed = incoming.passes_completed, "
                "passes_attempted = incoming.passes_attempted "
                f"FROM (VALUES {values_sql}) AS incoming({update_columns}) "
                "WHERE stats.id = incoming.id RETURNING stats.*",
                parameters
            ).fetchall()
            updated_count += len(saved_rows)
            for saved in saved_rows:
                player, team = identities[saved["id"]]
                imported.append({
                    **dict(saved), "player_name": player["name"],
                    "team_name": team["name"], "branch": team["branch"],
                    "category": team["category"]
                })
        insert_columns = (
            "week, game_id, player_id, team_id, points, receptions, "
            "interceptions, sacks, tackles, passes_completed, passes_attempted"
        )
        for offset in range(0, len(pending_inserts), 400):
            batch = pending_inserts[offset:offset + 400]
            values_sql = ", ".join(
                "(" + ", ".join(["%s"] * 11) + ")" for _ in batch
            )
            parameters = []
            identities = {}
            for week, game_id, player, team, values in batch:
                parameters.extend((week, game_id, player["id"], team["id"], *values))
                identities.setdefault((player["id"], team["id"]), (player, team))
            saved_rows = connection.execute(
                f"INSERT INTO player_week_stats ({insert_columns}) "
                f"VALUES {values_sql} RETURNING *",
                parameters
            ).fetchall()
            for saved in saved_rows:
                player, team = identities[(saved["player_id"], saved["team_id"])]
                imported.append({
                    **dict(saved), "player_name": player["name"],
                    "team_name": team["name"], "branch": team["branch"],
                    "category": team["category"]
                })
        # Official Wk sheets carry attendance as jersey numbers in an
        # "Asistencia" row. Save those check-ins in the source used by the
        # finals-eligibility view; repeated workbook imports remain idempotent.
        attendance_entries = []
        for week, resolved_rows in resolved_weeks.items():
            for player, team, row in resolved_rows:
                game_id = game_ids.get((week, row.get("game_index")))
                if row.get("attendance") and game_id is not None:
                    attendance_entries.append((
                        game_id, team["id"], player["id"],
                        row["jersey_number"], player["name"],
                    ))
        attendance_entries = list({entry[:3]: entry for entry in attendance_entries}.values())
        attendance_added = 0
        attendance_already_registered = 0
        if attendance_entries:
            attendance_game_ids = list({entry[0] for entry in attendance_entries})
            game_status = {
                row["id"]: row for row in connection.execute(
                    "SELECT id, status, is_friendly FROM games WHERE id = ANY(%s)",
                    (attendance_game_ids,),
                ).fetchall()
            }
            attendance_entries = [
                entry for entry in attendance_entries
                if entry[0] in game_status and not game_status[entry[0]]["is_friendly"]
            ]
        if attendance_entries:
            attendance_game_ids = list({entry[0] for entry in attendance_entries})
            session_values = ", ".join(["(%s, 'completed')"] * len(attendance_game_ids))
            connection.execute(
                "INSERT INTO game_live_sessions (game_id, state) VALUES "
                + session_values + " ON CONFLICT (game_id) DO NOTHING",
                attendance_game_ids,
            )
            current_attendance = connection.execute(
                """SELECT game_id, team_id, player_id FROM game_live_events
                WHERE kind = 'attendance' AND voided_at IS NULL
                  AND game_id = ANY(%s) AND player_id = ANY(%s)""",
                (attendance_game_ids, list({entry[2] for entry in attendance_entries})),
            ).fetchall()
            current_pairs = {
                (row["game_id"], row["team_id"], row["player_id"])
                for row in current_attendance
            }
            missing_attendance = [
                entry for entry in attendance_entries
                if entry[:3] not in current_pairs
            ]
            attendance_added = len(missing_attendance)
            attendance_already_registered = (
                len(attendance_entries) - attendance_added
            )
            for offset in range(0, len(missing_attendance), 400):
                batch = missing_attendance[offset:offset + 400]
                values_sql = ", ".join(["(%s, %s, 'attendance', %s, %s, %s, 1, 0, 0, %s)"] * len(batch))
                parameters = []
                for game_id, team_id, player_id, jersey_number, player_name in batch:
                    parameters.extend((
                        game_id, str(uuid4()), team_id, player_id,
                        f"#{jersey_number} {player_name}",
                        "Importada desde estadísticas",
                    ))
                connection.execute(
                    """INSERT INTO game_live_events (
                        game_id, client_id, kind, team_id, player_id,
                        player_label, period, minute, second, note
                    ) VALUES """ + values_sql,
                    parameters,
                )
        # Associate only imported rows when exactly one registered match fits.
        if imported:
            connection.execute(
                """
                UPDATE player_week_stats AS stats
                SET game_id = matched.game_id
                FROM (
                    SELECT stats_row.id AS stats_id, MIN(games.id) AS game_id
                    FROM player_week_stats AS stats_row
                    JOIN games ON games.week = stats_row.week
                      AND NOT games.is_friendly
                      AND stats_row.team_id IN (
                          games.home_team_id, games.away_team_id
                      )
                    WHERE stats_row.id = ANY(%s)
                      AND stats_row.game_id IS NULL
                    GROUP BY stats_row.id
                    HAVING COUNT(games.id) = 1
                ) AS matched
                WHERE stats.id = matched.stats_id
                """,
                ([saved["id"] for saved in imported],)
            )
        connection.commit()
        return {
            "imported": len(imported), "updated": updated_count,
            "retained_count": retained_count,
            "created": len(imported) - updated_count, "rows": imported,
            "skipped": skipped, "skipped_count": len(skipped),
            "preserved_weeks": sorted(preserved_weeks),
            "games": len(resolved_games),
            "attendance_added": attendance_added,
            "attendance_already_registered": attendance_already_registered,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def import_week_statistics(week, rows, games=None, *, link_existing_games_only=False, existing_records="update"):
    """Import one jornada; match existing games for stats-only official sheets."""
    return import_statistics_workbook(
        {week: rows},
        {week: games} if games is not None else None,
        link_existing_games_only=link_existing_games_only,
        existing_records=existing_records,
    )


def get_week_statistics(week):
    """Return all rows for one week with names resolved from the roster."""
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT stats.*, players.name AS player_name, teams.name AS team_name,
               teams.branch, teams.category, team_players.jersey_number
        FROM player_week_stats AS stats
        JOIN players ON players.id = stats.player_id
        JOIN teams ON teams.id = stats.team_id
        JOIN team_players ON team_players.team_id = stats.team_id
          AND team_players.player_id = stats.player_id
        WHERE stats.week = %s
        ORDER BY teams.branch, teams.category, teams.name, team_players.jersey_number
        """,
        (week,)
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def get_player_statistics_by_team(player_id):
    """Return separate season totals for each membership, never across teams."""
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT players.id AS player_id, players.name AS player_name,
            players.aka AS player_aka,
            CASE WHEN players.profile_photo_path IS NULL THEN NULL
                 ELSE '/media/profiles/' || players.profile_photo_path END AS profile_photo_url,
            teams.id AS team_id, teams.name AS team_name, teams.branch, teams.category,
            team_players.active,
            COUNT(DISTINCT stats.week)::INTEGER AS weeks,
            COALESCE(SUM(stats.points), 0)::INTEGER AS points,
            COALESCE(SUM(stats.receptions), 0)::INTEGER AS receptions,
            COALESCE(SUM(stats.interceptions), 0)::INTEGER AS interceptions,
            COALESCE(SUM(stats.sacks), 0)::INTEGER AS sacks,
            COALESCE(SUM(stats.tackles), 0)::INTEGER AS tackles,
            COALESCE(SUM(stats.passes_completed), 0)::INTEGER AS passes_completed,
            COALESCE(SUM(stats.passes_attempted), 0)::INTEGER AS passes_attempted
        FROM players
        LEFT JOIN team_players ON team_players.player_id = players.id
        LEFT JOIN teams ON teams.id = team_players.team_id
        LEFT JOIN player_week_stats AS stats
            ON stats.player_id = players.id AND stats.team_id = teams.id
        WHERE players.id = %s
        GROUP BY players.id, teams.id, team_players.active
        ORDER BY team_players.active DESC NULLS LAST,
                 teams.branch, teams.category, teams.name, teams.id
        """,
        (player_id,),
    ).fetchall()
    connection.close()
    results = []
    for row in rows:
        result = dict(row)
        result["completion_percentage"] = (
            round(result["passes_completed"] * 100 / result["passes_attempted"], 2)
            if result["passes_attempted"] > 0 else None
        )
        results.append(result)
    return results


def get_player_statistics(player_id, team_id=None):
    """Read the requested team, or the first membership when none is specified."""
    scopes = get_player_statistics_by_team(player_id)
    if team_id is not None:
        return next((row for row in scopes if row["team_id"] == team_id), None)
    return scopes[0] if scopes else None


def get_game_statistics(game_id, team_ids=None, player_id=None):
    """Return game-scoped rows filtered to authorized teams or one player."""
    connection = get_connection()
    conditions = ["stats.game_id = %s"]
    parameters = [game_id]
    if team_ids is not None:
        conditions.append("stats.team_id = ANY(%s)")
        parameters.append(list(team_ids))
    if player_id is not None:
        conditions.append("stats.player_id = %s")
        parameters.append(player_id)
    rows = connection.execute(
        f"""
        SELECT stats.*, players.name AS player_name, players.aka AS player_aka,
               teams.name AS team_name, team_players.jersey_number
        FROM player_week_stats AS stats
        JOIN players ON players.id = stats.player_id
        JOIN teams ON teams.id = stats.team_id
        JOIN team_players ON team_players.team_id = stats.team_id
          AND team_players.player_id = stats.player_id
        WHERE {' AND '.join(conditions)}
        ORDER BY teams.name, team_players.jersey_number
        """,
        tuple(parameters)
    ).fetchall()
    connection.close()
    results = []
    for row in rows:
        result = dict(row)
        result["completion_percentage"] = (
            round(result["passes_completed"] * 100 / result["passes_attempted"], 2)
            if result["passes_attempted"] else None
        )
        results.append(result)
    return results


def _rank_leaders(rows, score, limit):
    """Unique places: sporting metrics first, then stable administrative IDs."""
    ordered = sorted(rows, key=lambda row: (
        tuple(-value for value in score(row)),
        row["player_id"], row["team_id"],
    ))
    return [{**row, "rank": index + 1} for index, row in enumerate(ordered[:limit])]


LEADER_TIEBREAKERS = {
    "points": "Más puntos; después más recepciones.",
    "receptions": "Más recepciones; después más puntos personales.",
    "tackles": "Más tacleadas; después más capturas y más intercepciones.",
    "interceptions": "Más intercepciones; después más tacleadas.",
    "sacks": "Más capturas; después más tacleadas.",
    "completion_percentage": "Porcentaje exacto; después más intentos y más pases completos. Mínimo: 50 intentos acumulados.",
}

MINIMUM_PASS_ATTEMPTS = 50


def _leader_score(row, metric):
    if metric == "completion_percentage":
        return (Fraction(row["passes_completed"], row["passes_attempted"]),
                row["passes_attempted"], row["passes_completed"])
    secondary = {
        "points": ("receptions",),
        "receptions": ("points",),
        "tackles": ("sacks", "interceptions"),
        "interceptions": ("tackles",),
        "sacks": ("tackles",),
    }.get(metric, ())
    return tuple(row[key] for key in (metric, *secondary))


def get_leaderboards(branch, category, limit=5):
    """Return the leading players for every supported division metric."""
    connection = get_connection()
    unified = category_allows_cross_branch_games(category)
    rows = connection.execute(
        """
        SELECT players.id AS player_id, players.name AS player_name,
            players.aka AS player_aka,
            CASE
                WHEN players.profile_photo_path IS NULL THEN NULL
                ELSE '/media/profiles/' || players.profile_photo_path
            END AS profile_photo_url,
            teams.id AS team_id, teams.name AS team_name,
            team_players.jersey_number,
            SUM(stats.points)::INTEGER AS points,
            SUM(stats.receptions)::INTEGER AS receptions,
            SUM(stats.interceptions)::INTEGER AS interceptions,
            SUM(stats.sacks)::INTEGER AS sacks,
            SUM(stats.tackles)::INTEGER AS tackles,
            SUM(stats.passes_completed)::INTEGER AS passes_completed,
            SUM(stats.passes_attempted)::INTEGER AS passes_attempted,
            MAX(stats.week)::INTEGER AS latest_week
        FROM player_week_stats AS stats
        JOIN players ON players.id = stats.player_id
        JOIN teams ON teams.id = stats.team_id
        JOIN team_players ON team_players.team_id = stats.team_id
          AND team_players.player_id = stats.player_id
        WHERE LOWER(teams.category) = LOWER(%s)
          AND (%s OR LOWER(teams.branch) = LOWER(%s))
        GROUP BY players.id, players.name, players.aka,
                 players.profile_photo_path, teams.id, teams.name,
                 team_players.jersey_number
        """,
        (category.strip(), unified, branch.strip())
    ).fetchall()
    connection.close()

    result = {}
    for metric in ("receptions", "points", "tackles", "interceptions", "sacks"):
        ranked = _rank_leaders(
            (row for row in rows if row[metric] > 0),
            lambda row: _leader_score(row, metric), limit,
        )
        result[metric] = [
            {"player_id": row["player_id"], "player_name": row["player_name"],
             "player_aka": row["player_aka"],
             "profile_photo_url": row["profile_photo_url"],
             "team_id": row["team_id"], "team_name": row["team_name"],
             "jersey_number": row["jersey_number"], "value": row[metric],
             "rank": row["rank"]}
            for row in ranked
        ]

    latest_week = max((row["latest_week"] for row in rows), default=0)
    minimum_attempts = MINIMUM_PASS_ATTEMPTS  # Completed + incomplete attempts across all weeks
    passing_ranked = _rank_leaders(
        (row for row in rows if row["passes_attempted"] > 0
         and row["passes_attempted"] >= minimum_attempts),
        lambda row: _leader_score(row, "completion_percentage"),
        limit,
    )
    result["completion_percentage"] = [
        {"player_id": row["player_id"], "player_name": row["player_name"],
         "player_aka": row["player_aka"],
         "profile_photo_url": row["profile_photo_url"],
         "team_id": row["team_id"], "team_name": row["team_name"],
         "jersey_number": row["jersey_number"],
         "value": round(row["passes_completed"] * 100 / row["passes_attempted"], 2),
         "passes_completed": row["passes_completed"],
         "passes_attempted": row["passes_attempted"], "rank": row["rank"]}
        for row in passing_ranked
    ]
    result["tie_breakers"] = {
        metric: rule + " Si persiste igualdad: menor ID del jugador y después del equipo, como orden administrativo."
        for metric, rule in LEADER_TIEBREAKERS.items()
    }
    result["passing_qualification"] = {
        "latest_week": latest_week, "minimum_attempts": minimum_attempts
    }
    return result



