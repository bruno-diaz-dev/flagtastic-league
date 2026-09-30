"""enforce case insensitive team identity

Revision ID: 9896321cb65f
Revises: f52b9c4a731d
Create Date: 2026-09-30 00:59:07.276947

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '9896321cb65f'
down_revision: Union[str, Sequence[str], None] = 'f52b9c4a731d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # API validation keeps display casing, so the database identity must compare
    # the stored name without considering leading/trailing whitespace or case.
    op.drop_constraint(
        "teams_name_branch_category_key",
        "teams",
        type_="unique",
    )
    op.execute(
        """
        CREATE UNIQUE INDEX teams_normalized_name_branch_category_key
        ON teams (LOWER(BTRIM(name)), branch, category)
        """
    )


def downgrade() -> None:
    op.drop_index(
        "teams_normalized_name_branch_category_key",
        table_name="teams",
    )
    op.create_unique_constraint(
        "teams_name_branch_category_key",
        "teams",
        ["name", "branch", "category"],
    )
