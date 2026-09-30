"""Canonical league division rules shared by APIs and importers."""


def canonicalize_division(branch, category):
    """Normalize a division and enforce the league-wide U12 mixed branch."""
    normalized_branch = str(branch or "").strip().lower()
    normalized_category = str(category or "").strip().lower()
    if normalized_category == "u12":
        normalized_branch = "mixto"
    return normalized_branch, normalized_category


def teams_share_game_division(home_team, away_team):
    """Allow cross-branch pairings only inside the unified U12 category."""
    home_branch = str(home_team.get("branch") or "").strip().lower()
    away_branch = str(away_team.get("branch") or "").strip().lower()
    home_category = str(home_team.get("category") or "").strip().lower()
    away_category = str(away_team.get("category") or "").strip().lower()
    if home_category != away_category:
        return False
    return home_category == "u12" or home_branch == away_branch
