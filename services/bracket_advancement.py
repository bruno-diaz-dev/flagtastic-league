"""Resolve pre-created playoff games once both feeder games have final scores."""


def resolve_completed_bracket_slots(connection, source_game_id):
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
        result = connection.execute("""
            UPDATE games
            SET home_team_id=%s, away_team_id=%s,
                home_pending_label=NULL, away_pending_label=NULL
            WHERE id=%s AND home_team_id IS NULL AND away_team_id IS NULL
            RETURNING id
        """, (teams[0], teams[1], slot["target_game_id"])).fetchone()
        if result:
            updated.append(result["id"])
    return updated

