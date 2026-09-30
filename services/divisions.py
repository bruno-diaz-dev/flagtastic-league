"""Canonical league division rules shared by APIs and importers."""


def canonicalize_division(branch, category):
    """Normalize a division and enforce the league-wide U12 mixed branch."""
    normalized_branch = str(branch or "").strip().lower()
    normalized_category = str(category or "").strip().lower()
    if normalized_category == "u12":
        normalized_branch = "mixto"
    return normalized_branch, normalized_category
