"""Tests for CURP birth-date and completed-age calculations."""

from datetime import date

from services.curp import calendar_age_from_curp


CURP = "DIBB961215HASXXX01"


def test_curp_age_stays_lower_until_birthday():
    assert calendar_age_from_curp(CURP, as_of=date(2026, 12, 14)) == 29


def test_curp_age_increments_on_birthday():
    assert calendar_age_from_curp(CURP, as_of=date(2026, 12, 15)) == 30


def test_curp_age_remains_incremented_after_birthday():
    assert calendar_age_from_curp(CURP, as_of=date(2026, 12, 16)) == 30
