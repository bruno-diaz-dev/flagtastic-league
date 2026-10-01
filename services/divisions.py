"""Canonical league division rules shared by APIs and importers."""


CROSS_BRANCH_GAME_CATEGORIES = {"u8", "u10", "u12"}


def normalize_division(branch, category):
    """Normalize branch and category text without changing league identity."""
    normalized_branch = str(branch or "").strip().lower()
    normalized_category = str(category or "").strip().lower()
    return normalized_branch, normalized_category


def category_allows_cross_branch_games(category):
    """Return whether a youth category competes as one unified division."""
    return str(category or "").strip().lower() in CROSS_BRANCH_GAME_CATEGORIES


def teams_share_game_division(home_team, away_team):
    """Allow cross-branch pairings in the unified U8 through U12 categories."""
    home_branch = str(home_team.get("branch") or "").strip().lower()
    away_branch = str(away_team.get("branch") or "").strip().lower()
    home_category = str(home_team.get("category") or "").strip().lower()
    away_category = str(away_team.get("category") or "").strip().lower()
    if home_category != away_category:
        return False
    return (
        category_allows_cross_branch_games(home_category)
        or home_branch == away_branch
    )
