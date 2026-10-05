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


def age_from_birth_date(birth_date: date, as_of: date | None = None) -> int:
    """Calculate completed age for an explicitly supplied birth date."""
    reference = as_of or date.today()
    if birth_date > reference:
        raise InvalidCurpBirthDate("La fecha de nacimiento no puede ser futura")
    return reference.year - birth_date.year - (
        (reference.month, reference.day) < (birth_date.month, birth_date.day)
    )


def resolve_player_identity(curp, identity_type, birth_date, legacy_age):
    """Keep short documents explicit and preserve standard CURP validation."""
    if not curp:
        raise ValueError("El identificador no puede estar vacío")
    if identity_type == "provisional":
        if len(curp) >= 18:
            raise ValueError("Usa la opción CURP para identificadores de 18 caracteres")
        if birth_date is None:
            raise ValueError("Indica la fecha de nacimiento para el documento provisional")
        return birth_date, age_from_birth_date(birth_date)
    if len(curp) != 18:
        raise ValueError("La CURP debe contener 18 caracteres. Para un documento escolar corto, selecciona identificación provisional")
    try:
        decoded = birth_date_from_curp(curp)
        return decoded, age_from_birth_date(decoded)
    except InvalidCurpBirthDate:
        # Retain compatibility with preexisting imports and legacy test data.
        if legacy_age is None:
            raise ValueError("La CURP no contiene una fecha valida")
        return None, legacy_age
