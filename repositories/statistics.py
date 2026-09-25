"""Persistence and aggregate queries for weekly player statistics."""

from database import get_connection


class StatisticsValidationError(Exception):
    """Raised when imported statistics conflict with league data."""


def import_statistics_workbook(weeks, games=None):
    """Atomically replace included weekly statistics and inferred games."""
    connection = get_connection()
    try:
        teams = connection.execute(
            "SELECT id, name, branch, category FROM teams"
        ).fetchall()
        teams_by_identity = {
            (team["branch"].strip().casefold(),
             team["category"].strip().casefold(),
             team["name"].strip().casefold()): team
            for team in teams
        }
        resolved_weeks = {}
        for week, rows in weeks.items():
            resolved_rows = []
            seen_memberships = set()
            for row_number, row in enumerate(rows, start=2):
                team = teams_by_identity.get((
                    row["branch"].strip().casefold(),
                    row["category"].strip().casefold(),
                    row["team"].strip().casefold()
                ))
                if team is None:
                    raise StatisticsValidationError(
                        f"Jornada {week}, fila {row_number}: no existe "
                        "el equipo en esa rama y categoria"
                    )
                player = connection.execute(
                    """
                    SELECT players.id, players.name
                    FROM team_players
                    JOIN players ON players.id = team_players.player_id
                    WHERE team_players.team_id = %s
                      AND team_players.jersey_number = %s
                    """,
                    (team["id"], row["jersey_number"])
                ).fetchone()
                if player is None:
                    raise StatisticsValidationError(
                        f"Jornada {week}, fila {row_number}: no existe el "
                        f"numero {row['jersey_number']} en {row['team']}"
                    )
                membership = (
                    row.get("game_index"), player["id"], team["id"]
                )
                if membership in seen_memberships:
                    raise StatisticsValidationError(
                        f"Jornada {week}, fila {row_number}: jugador repetido"
                    )
                seen_memberships.add(membership)
                resolved_rows.append((player, team, row))
            resolved_weeks[week] = resolved_rows

        resolved_games = []
        for week, week_games in (games or {}).items():
            for game_index, game in enumerate(week_games):
                game = {**game, "game_index": game_index}
                division = (
                    game["branch"].strip().casefold(),
                    game["category"].strip().casefold()
                )
                home = teams_by_identity.get(
                    (*division, game["home_team"].strip().casefold())
                )
                away = teams_by_identity.get(
                    (*division, game["away_team"].strip().casefold())
                )
                if home is None or away is None:
                    missing = game["home_team"] if home is None else game["away_team"]
                    raise StatisticsValidationError(
                        f"Jornada {week}: no existe el equipo {missing} en esa division"
                    )
                resolved_games.append((week, home["id"], away["id"], game))

        # Validation finishes before deleting anything, so a bad row leaves all
        # previously published jornadas untouched.
        connection.execute(
            "DELETE FROM player_week_stats WHERE week = ANY(%s)",
            (list(resolved_weeks),)
        )
        game_ids = {}
        used_existing_game_ids = set()
        for week, home_team_id, away_team_id, game in resolved_games:
            existing_candidates = connection.execute(
                """
                SELECT id FROM games
                WHERE week = %s AND home_team_id = %s AND away_team_id = %s
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
                saved_game = connection.execute(
                    """
                    INSERT INTO games (
                        home_team_id, away_team_id, home_score, away_score, week
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (home_team_id, away_team_id, game["home_score"],
                     game["away_score"], week)
                ).fetchone()
            else:
                saved_game = connection.execute(
                    """
                    UPDATE games SET home_score = %s, away_score = %s
                    WHERE id = %s RETURNING id
                    """,
                    (game["home_score"], game["away_score"], existing["id"])
                ).fetchone()
            used_existing_game_ids.add(saved_game["id"])
            game_ids[(week, game["game_index"])] = saved_game["id"]
        imported = []
        for week, resolved_rows in resolved_weeks.items():
            for player, team, row in resolved_rows:
                game_id = game_ids.get((week, row.get("game_index")))
                created = connection.execute(
                    """
                    INSERT INTO player_week_stats (
                        week, game_id, player_id, team_id, points, receptions,
                        interceptions, sacks, tackles, passes_completed,
                        passes_attempted
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (week, game_id, player["id"], team["id"], row["points"],
                     row["receptions"], row["interceptions"], row["sacks"],
                     row["tackles"], row["passes_completed"],
                     row["passes_attempted"])
                ).fetchone()
                imported.append({
                    **dict(created), "player_name": player["name"],
                    "team_name": team["name"], "branch": team["branch"],
                    "category": team["category"]
                })
        # Associate rows only when a team has one unambiguous game that week.
        connection.execute(
            """
            UPDATE player_week_stats AS stats
            SET game_id = matched.game_id
            FROM (
                SELECT stats_row.id AS stats_id, MIN(games.id) AS game_id
                FROM player_week_stats AS stats_row
                JOIN games ON games.week = stats_row.week
                  AND stats_row.team_id IN (
                      games.home_team_id, games.away_team_id
                  )
                WHERE stats_row.week = ANY(%s)
                GROUP BY stats_row.id
                HAVING COUNT(games.id) = 1
            ) AS matched
            WHERE stats.id = matched.stats_id
            """,
            (list(resolved_weeks),)
        )
        connection.commit()
        return imported
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def import_week_statistics(week, rows, games=None):
    """Compatibility wrapper for a compact single-jornada workbook."""
    return import_statistics_workbook(
        {week: rows},
        {week: games} if games is not None else None
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


def get_player_statistics(player_id):
    """Return totals derived from a player's weekly records."""
    connection = get_connection()
    row = connection.execute(
        """
        SELECT players.id AS player_id, players.name AS player_name,
            players.aka AS player_aka,
            CASE
                WHEN players.profile_photo_path IS NULL THEN NULL
                ELSE '/media/profiles/' || players.profile_photo_path
            END AS profile_photo_url,
            COUNT(stats.id)::INTEGER AS weeks,
            COALESCE(SUM(stats.points), 0)::INTEGER AS points,
            COALESCE(SUM(stats.receptions), 0)::INTEGER AS receptions,
            COALESCE(SUM(stats.interceptions), 0)::INTEGER AS interceptions,
            COALESCE(SUM(stats.sacks), 0)::INTEGER AS sacks,
            COALESCE(SUM(stats.tackles), 0)::INTEGER AS tackles,
            COALESCE(SUM(stats.passes_completed), 0)::INTEGER AS passes_completed,
            COALESCE(SUM(stats.passes_attempted), 0)::INTEGER AS passes_attempted
        FROM players
        LEFT JOIN player_week_stats AS stats ON stats.player_id = players.id
        WHERE players.id = %s
        GROUP BY players.id, players.name
        """,
        (player_id,)
    ).fetchone()
    connection.close()
    if row is None:
        return None
    result = dict(row)
    result["completion_percentage"] = (
        round(result["passes_completed"] * 100 / result["passes_attempted"], 2)
        if result["passes_attempted"] > 0 else None
    )
    return result


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


def get_leaderboards(branch, category, limit=5):
    """Return the leading players for every supported division metric."""
    connection = get_connection()
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
        WHERE LOWER(teams.branch) = LOWER(%s)
          AND LOWER(teams.category) = LOWER(%s)
        GROUP BY players.id, players.name, players.aka,
                 players.profile_photo_path, teams.id, teams.name,
                 team_players.jersey_number
        """,
        (branch.strip(), category.strip())
    ).fetchall()
    connection.close()

    result = {}
    for metric in ("receptions", "points", "tackles", "interceptions", "sacks"):
        ranked = sorted(
            (row for row in rows if row[metric] > 0),
            key=lambda row: (-row[metric], row["player_name"].casefold(),
                             row["team_name"].casefold())
        )[:limit]
        result[metric] = [
            {"player_id": row["player_id"], "player_name": row["player_name"],
             "player_aka": row["player_aka"],
             "profile_photo_url": row["profile_photo_url"],
             "team_id": row["team_id"], "team_name": row["team_name"],
             "jersey_number": row["jersey_number"], "value": row[metric]}
            for row in ranked
        ]

    latest_week = max((row["latest_week"] for row in rows), default=0)
    minimum_attempts = 0 if latest_week <= 3 else 30
    passing_ranked = sorted(
        (row for row in rows if row["passes_attempted"] > 0
         and row["passes_attempted"] >= minimum_attempts),
        key=lambda row: (-(row["passes_completed"] / row["passes_attempted"]),
                         -row["passes_attempted"], row["player_name"].casefold())
    )[:limit]
    result["completion_percentage"] = [
        {"player_id": row["player_id"], "player_name": row["player_name"],
         "player_aka": row["player_aka"],
         "profile_photo_url": row["profile_photo_url"],
         "team_id": row["team_id"], "team_name": row["team_name"],
         "jersey_number": row["jersey_number"],
         "value": round(row["passes_completed"] * 100 / row["passes_attempted"], 2),
         "passes_completed": row["passes_completed"],
         "passes_attempted": row["passes_attempted"]}
        for row in passing_ranked
    ]
    result["passing_qualification"] = {
        "latest_week": latest_week, "minimum_attempts": minimum_attempts
    }
    return result
