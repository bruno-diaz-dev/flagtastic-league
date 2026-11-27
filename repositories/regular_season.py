"""Shared SQL rules for which games belong to the regular season.

Finals eligibility counts only regular-season games:

- Playoffs (semifinals, finals and third-place games) start on the first
  week that holds a bracket slot. That whole week and later ones are
  excluded, including playoff games that have no bracket slot of their own
  (for example a direct final).
- Postponed games were not played on that date; the rescheduled game, if
  any, is a separate record and is the one that counts.
"""

# First playoff week, or no limit while no bracket has been scheduled yet.
FIRST_PLAYOFF_WEEK_SQL = (
    "COALESCE((SELECT MIN(playoff.week) FROM game_bracket_slots AS playoff), "
    "2147483647)"
)


def regular_season_game_sql(alias="g"):
    """Conditions a games row (by ``alias``) must meet to be regular season."""
    return (
        f"NOT {alias}.is_friendly "
        f"AND {alias}.status <> 'postponed' "
        f"AND {alias}.week < {FIRST_PLAYOFF_WEEK_SQL} "
        f"AND NOT EXISTS (SELECT 1 FROM game_bracket_slots AS slots "
        f"WHERE slots.target_game_id = {alias}.id)"
    )
