"""CURP birth-date helpers used by player registration and roster imports."""

from datetime import date


class InvalidCurpBirthDate(ValueError):
    """Raised when the birth-date segment of a CURP is not usable."""


def birth_date_from_curp(curp: str) -> date:
    """Decode the CURP YYMMDD segment and its official century marker."""
    normalized = curp.strip().upper()
    if len(normalized) != 18:
        raise InvalidCurpBirthDate("La CURP debe contener 18 caracteres")

    date_segment = normalized[4:10]
    century_marker = normalized[16]
    if not date_segment.isdigit() or not century_marker.isalnum():
        raise InvalidCurpBirthDate("La CURP no contiene una fecha valida")

    # RENAPO uses a digit for births before 2000 and a letter from 2000 on.
    century = 1900 if century_marker.isdigit() else 2000
    try:
        birth_date = date(
            century + int(date_segment[:2]),
            int(date_segment[2:4]),
            int(date_segment[4:6])
        )
    except ValueError as error:
        raise InvalidCurpBirthDate("La CURP no contiene una fecha valida") from error

    if birth_date > date.today():
        raise InvalidCurpBirthDate("La fecha de nacimiento no puede ser futura")
    return birth_date


def calendar_age_from_curp(curp: str, year: int | None = None) -> int:
    """Return the age the person turns during the selected calendar year."""
    birth_date = birth_date_from_curp(curp)
    return (year or date.today().year) - birth_date.year
