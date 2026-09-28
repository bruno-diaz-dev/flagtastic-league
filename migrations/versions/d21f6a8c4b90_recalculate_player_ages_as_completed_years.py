"""recalculate player ages as completed years

Revision ID: d21f6a8c4b90
Revises: c7a4d2e91f30
"""

from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d21f6a8c4b90"
down_revision: Union[str, Sequence[str], None] = "c7a4d2e91f30"
branch_labels = None
depends_on = None


def _birth_date(curp: str):
    normalized = (curp or "").strip().upper()
    if len(normalized) != 18:
        return None
    segment = normalized[4:10]
    marker = normalized[16]
    if not segment.isdigit() or not marker.isalnum():
        return None
    century = 1900 if marker.isdigit() else 2000
    try:
        return date(
            century + int(segment[:2]),
            int(segment[2:4]),
            int(segment[4:6]),
        )
    except ValueError:
        return None


def _age(birth_date: date, reference_date: date, completed: bool) -> int:
    age = reference_date.year - birth_date.year
    if completed and (
        (reference_date.month, reference_date.day)
        < (birth_date.month, birth_date.day)
    ):
        age -= 1
    return age


def _recalculate(completed: bool) -> None:
    connection = op.get_bind()
    today = date.today()
    rows = connection.execute(
        sa.text("SELECT id, curp FROM players")
    ).mappings()
    for row in rows:
        birth_date = _birth_date(row["curp"])
        if birth_date is None or birth_date > today:
            continue
        connection.execute(
            sa.text("UPDATE players SET age = :age WHERE id = :id"),
            {
                "age": _age(birth_date, today, completed),
                "id": row["id"],
            },
        )


def upgrade() -> None:
    """Backfill stored ages using birthdays already reached."""
    _recalculate(completed=True)


def downgrade() -> None:
    """Restore the previous age-reached-during-calendar-year behavior."""
    _recalculate(completed=False)
