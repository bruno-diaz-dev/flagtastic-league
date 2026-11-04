"""Explicit league-approved credits for a removed result; never extra games."""

# Verified before its removal: /games/258, BlackMamba 0-42 Vikingos, U12, week 4.
# The administrator approved ONLY Vikingos' 42 points for: no win/game played
# and no effect on BlackMamba. This entry can be removed to reverse the credit.
POINTS_FOR_ADJUSTMENTS = (
    {"source_game_id": 258, "home_team_id": 62, "away_team_id": 61,
     "week": 4, "home_score": 0, "away_score": 42,
     "team_id": 61, "team_name": "Vikingos", "category": "u12", "points_for": 42},
)


def apply_points_for_adjustments(connection, standings, category):
    """Apply each approved credit once to a freshly calculated standing.

    Do not add a credit if its source record or a completed replacement already
    exists. This prevents an imported copy of the result earning points twice.
    """
    teams = {row["team_id"]: row for row in standings}
    for adjustment in POINTS_FOR_ADJUSTMENTS:
        team = teams.get(adjustment["team_id"])
        if (team is None or category.strip().casefold() != adjustment["category"]
                or team["team_name"].strip().casefold() != adjustment["team_name"].casefold()):
            continue
        existing = connection.execute("""
            SELECT EXISTS (
                SELECT 1 FROM games WHERE id = %s OR (
                    week = %s AND status = 'completed' AND NOT is_friendly AND (
                        (home_team_id = %s AND away_team_id = %s AND home_score = %s AND away_score = %s)
                        OR (home_team_id = %s AND away_team_id = %s AND home_score = %s AND away_score = %s)
                    )
                )
            ) AS present
        """, (adjustment["source_game_id"], adjustment["week"],
              adjustment["home_team_id"], adjustment["away_team_id"], adjustment["home_score"], adjustment["away_score"],
              adjustment["away_team_id"], adjustment["home_team_id"], adjustment["away_score"], adjustment["home_score"])).fetchone()["present"]
        if not existing:
            team["points_for"] += adjustment["points_for"]
