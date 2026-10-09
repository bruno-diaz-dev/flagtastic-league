"""Season-specific cutoff for representative roster changes."""

from datetime import datetime
from zoneinfo import ZoneInfo


ROSTER_TIMEZONE = ZoneInfo("America/Mexico_City")
ROSTER_CLOSES_AT = datetime(2026, 10, 16, tzinfo=ROSTER_TIMEZONE)
ROSTER_CLOSED_MESSAGE = (
    "El roster cerro el 16 de octubre de 2026 a las 00:00 "
    "(hora de Ciudad de Mexico). Solo administradores pueden realizar cambios."
)


def roster_is_closed():
    """Use server time, including the exact midnight boundary."""
    return datetime.now(ROSTER_TIMEZONE) >= ROSTER_CLOSES_AT
