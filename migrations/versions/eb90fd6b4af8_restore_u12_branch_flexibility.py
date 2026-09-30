"""restore u12 branch flexibility

Revision ID: eb90fd6b4af8
Revises: 076ebba7c2fe
Create Date: 2026-09-30 10:37:49.988390

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'eb90fd6b4af8'
down_revision: Union[str, Sequence[str], None] = '076ebba7c2fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Repair databases that applied the superseded U12 branch constraint."""
    op.execute(
        """
        ALTER TABLE teams
        DROP CONSTRAINT IF EXISTS teams_u12_mixed_branch_check
        """
    )


def downgrade() -> None:
    """Keep U12 branches flexible; restoring the rejected rule is unsafe."""
