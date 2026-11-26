"""Create playoff placement games once both feeder games have final scores."""


def resolve_completed_bracket_slots(connection, source_game_id):
    slots = connection.execute("""
        SELECT * FROM game_bracket_slots
        WHERE target_game_id IS NULL
          AND (source_game_id=%s OR opponent_game_id=%s)
        ORDER BY id FOR UPDATE
    """, (source_game_id, source_game_id)).fetchall()
    created = []
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
        values = [teams[0], teams[1], slot["week"], slot["field_number"],
                  slot["start_time"], False]
        columns = "home_team_id,away_team_id,week,field_number,start_time,is_friendly"
        placeholders = "%s,%s,%s,%s,%s,%s"
        if slot["game_date"] is not None or slot["venue"] is not None:
            columns += ",game_date,venue"
            placeholders += ",%s,%s"
            values.extend([slot["game_date"], slot["venue"]])
        game = connection.execute(
            f"INSERT INTO games ({columns}) VALUES ({placeholders}) RETURNING id",
            values,
        ).fetchone()
        connection.execute("UPDATE game_bracket_slots SET target_game_id=%s WHERE id=%s",
                           (game["id"], slot["id"]))
        created.append(game["id"])
    return created
