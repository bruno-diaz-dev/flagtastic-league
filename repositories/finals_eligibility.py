"""Administrator reports for regular-season finals eligibility."""

from database import get_connection


def get_players_below_finals_attendance():
    """Return active roster members below the threshold in their category."""
    with get_connection() as connection:
        rows = connection.execute("""
            WITH regular_games AS (
                SELECT g.id AS game_id, g.home_team_id AS team_id, home.category
                FROM games g
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                WHERE NOT g.is_friendly AND home.category = away.category
                  AND NOT EXISTS (
                      SELECT 1 FROM game_bracket_slots slots
                      WHERE slots.target_game_id = g.id
                  )
                UNION ALL
                SELECT g.id AS game_id, g.away_team_id AS team_id, away.category
                FROM games g
                JOIN teams home ON home.id = g.home_team_id
                JOIN teams away ON away.id = g.away_team_id
                WHERE NOT g.is_friendly AND home.category = away.category
                  AND NOT EXISTS (
                      SELECT 1 FROM game_bracket_slots slots
                      WHERE slots.target_game_id = g.id
                  )
            ), team_totals AS (
                SELECT team_id, category, COUNT(*)::int AS scheduled_games
                FROM regular_games
                GROUP BY team_id, category
            ), player_attendance AS (
                SELECT e.team_id, e.player_id, rg.category,
                       COUNT(DISTINCT e.game_id)::int AS attended_games
                FROM game_live_events e
                JOIN games g ON g.id = e.game_id AND g.status = 'completed'
                JOIN regular_games rg ON rg.game_id = g.id AND rg.team_id = e.team_id
                WHERE e.kind = 'attendance' AND e.voided_at IS NULL
                GROUP BY e.team_id, e.player_id, rg.category
            )
            SELECT t.id AS team_id, t.name AS team_name, t.branch, t.category,
                   tp.player_id, tp.jersey_number,
                   COALESCE(NULLIF(p.aka, ''), p.name) AS player_name,
                   totals.scheduled_games,
                   COALESCE(attendance.attended_games, 0) AS attended_games
            FROM team_players tp
            JOIN teams t ON t.id = tp.team_id
            JOIN players p ON p.id = tp.player_id
            JOIN team_totals totals ON totals.team_id = tp.team_id
            LEFT JOIN player_attendance attendance
              ON attendance.team_id = tp.team_id
             AND attendance.player_id = tp.player_id
             AND attendance.category = t.category
            WHERE tp.active
            ORDER BY t.category, t.branch, t.name, p.name, tp.player_id
        """).fetchall()

    ineligible = []
    for row in rows:
        total = row["scheduled_games"]
        required = total // 2 + 1
        attended = row["attended_games"]
        if attended < required:
            ineligible.append({**dict(row), "required_games": required})
    return ineligible

