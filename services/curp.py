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


def calendar_age_from_curp(curp: str, as_of: date | None = None) -> int:
    """Return completed years of age as of the selected date."""
    birth_date = birth_date_from_curp(curp)
    reference_date = as_of or date.today()
    if birth_date > reference_date:
        raise InvalidCurpBirthDate("La fecha de nacimiento no puede ser futura")
    return (
        reference_date.year
        - birth_date.year
        - ((reference_date.month, reference_date.day) < (birth_date.month, birth_date.day))
    )
