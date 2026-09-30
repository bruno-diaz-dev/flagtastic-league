"""Resolve abbreviated upload labels against registered league teams."""

from difflib import SequenceMatcher
import re
import unicodedata

from services.divisions import canonicalize_division


_NAME_STOP_WORDS = {"de", "del", "el", "la", "las", "los", "y"}
_DIVISION_TOKENS = {
    "fem", "femenil", "var", "varonil", "mix", "mixto", "libre",
    "u6", "u8", "u10", "u12", "u14", "u16", "u18",
    "6", "8", "10", "12", "14", "16", "18",
}


def normalize_team_text(value):
    """Return accent-insensitive lowercase words for matching and identity."""
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(
        character for character in text
        if not unicodedata.combining(character)
    )
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def _name_tokens(value, strip_division=False):
    ignored = _NAME_STOP_WORDS | (_DIVISION_TOKENS if strip_division else set())
    return [
        token for token in normalize_team_text(value).split()
        if token not in ignored
    ]


def _token_score(source, target):
    if source == target:
        return 1.0
    if min(len(source), len(target)) >= 3 and (
        source.startswith(target) or target.startswith(source)
    ):
        return 0.97
    return SequenceMatcher(None, source, target).ratio()


def team_name_match_score(label, registered_name):
    """Score an exact, partial, or abbreviated label from zero to one.

    Upload labels may omit connector words or shorten a meaningful word, as in
    ``Diablos Ama`` for ``Diablos del Sol Amarillo``. Extra registered-name
    words are tolerated, but short generic labels remain ambiguous when more
    than one registered team fits them.
    """
    label_tokens = _name_tokens(label, strip_division=True)
    registered_tokens = _name_tokens(registered_name)
    if not label_tokens or not registered_tokens:
        return 0.0

    normalized_label = " ".join(label_tokens)
    normalized_registered = " ".join(registered_tokens)
    if normalized_label == normalized_registered:
        return 1.0

    available = set(range(len(registered_tokens)))
    token_scores = []
    for source in label_tokens:
        candidates = [
            (_token_score(source, registered_tokens[index]), index)
            for index in available
        ]
        if not candidates:
            return 0.0
        score, index = max(candidates)
        if score < 0.58:
            return 0.0
        token_scores.append(score)
        available.remove(index)

    label_coverage = sum(token_scores) / len(token_scores)
    registered_coverage = len(token_scores) / len(registered_tokens)
    sequence_score = SequenceMatcher(
        None, normalized_label, normalized_registered
    ).ratio()
    return max(
        sequence_score,
        label_coverage * 0.88 + registered_coverage * 0.12,
    )


def rank_team_matches(label, teams, branch=None, category=None):
    """Rank registered teams, optionally restricting them to one division."""
    normalized_branch, normalized_category = canonicalize_division(
        branch, category
    )
    ranked = []
    for team in teams:
        team_branch, team_category = canonicalize_division(
            team["branch"], team["category"]
        )
        if normalized_category and team_category != normalized_category:
            continue
        if normalized_branch and team_branch != normalized_branch:
            continue
        ranked.append((team_name_match_score(label, team["name"]), team))
    ranked.sort(key=lambda candidate: candidate[0], reverse=True)
    return ranked


def match_team_name(label, teams, branch=None, category=None):
    """Return one confident team match, never guessing an ambiguous label."""
    ranked = rank_team_matches(label, teams, branch, category)
    if not ranked or ranked[0][0] < 0.76:
        return None
    if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < 0.06:
        return None
    return ranked[0][1]
