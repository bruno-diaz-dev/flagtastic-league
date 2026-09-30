"""normalize u12 teams to mixed

Revision ID: 076ebba7c2fe
Revises: 9896321cb65f
Create Date: 2026-09-30 09:44:22.978179

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '076ebba7c2fe'
down_revision: Union[str, Sequence[str], None] = '9896321cb65f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Retain the revision without rewriting the branch of existing teams."""


def downgrade() -> None:
    """No schema change was introduced by this compatibility revision."""
