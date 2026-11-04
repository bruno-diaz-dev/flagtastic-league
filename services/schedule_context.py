"""Calendar dates and venue labels shared by schedule readers."""

from datetime import date, datetime
import unicodedata


def venue_key(value):
    return " ".join(str(value or "").split()).casefold()


def clean_venue(value):
    return " ".join(str(value or "").split()) or None


def parse_schedule_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            pass
    return None


def context_header(values, previous):
    """Read one block header; a bad date never inherits the previous block's day."""
    def key(value):
        text = unicodedata.normalize("NFKD", str(value or ""))
        return " ".join("".join(c for c in text if not unicodedata.combining(c)).casefold().strip().rstrip(":").split())
    labels = {"sede": "venue", "venue": "venue", "fecha": "game_date", "date": "game_date"}
    found = {}
    for index, value in enumerate(values):
        label = labels.get(key(value))
        if not label:
            continue
        following = None
        for candidate in values[index + 1:]:
            if key(candidate) in labels:
                break
            if candidate is not None and str(candidate).strip():
                following = candidate
                break
        found[label] = following
    if not found:
        return None
    result = dict(previous)
    if "venue" in found:
        result.update(venue=clean_venue(found["venue"]), game_date=None, date_required=False)
    if "game_date" in found:
        parsed = parse_schedule_date(found["game_date"])
        result.update(game_date=parsed, date_required=parsed is None)
    return result


def context_fields(context):
    """Keep old files' response shape while carrying explicit block metadata."""
    result = {}
    if context.get("game_date") is not None:
        result["game_date"] = context["game_date"].isoformat()
    if context.get("venue"):
        result["venue"] = context["venue"]
    if context.get("date_required"):
        result["date_required"] = True
    return result
