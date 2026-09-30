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
    """Move every U12 team into the mixed branch without losing identities."""
    op.drop_index(
        "teams_normalized_name_branch_category_key",
        table_name="teams",
    )
    # Names that only differed by their former branch would collide after the
    # update. Preserve each team and its foreign-key history by adding the old
    # branch abbreviation to the non-mixed records in those duplicate groups.
    op.execute(
        """
        DO $$
        DECLARE
            duplicate RECORD;
            candidate TEXT;
        BEGIN
            FOR duplicate IN
                SELECT teams.id, teams.name, LOWER(BTRIM(teams.branch)) AS branch
                FROM teams
                JOIN (
                    SELECT LOWER(BTRIM(name)) AS normalized_name
                    FROM teams
                    WHERE LOWER(BTRIM(category)) = 'u12'
                    GROUP BY LOWER(BTRIM(name))
                    HAVING COUNT(*) > 1
                ) AS collisions
                  ON collisions.normalized_name = LOWER(BTRIM(teams.name))
                WHERE LOWER(BTRIM(teams.category)) = 'u12'
                  AND LOWER(BTRIM(teams.branch)) <> 'mixto'
                ORDER BY teams.id
            LOOP
                candidate := BTRIM(duplicate.name) || CASE duplicate.branch
                    WHEN 'femenil' THEN ' Fem'
                    WHEN 'varonil' THEN ' Var'
                    ELSE ' ' || INITCAP(duplicate.branch)
                END;
                IF EXISTS (
                    SELECT 1 FROM teams
                    WHERE id <> duplicate.id
                      AND LOWER(BTRIM(category)) = 'u12'
                      AND LOWER(BTRIM(name)) = LOWER(candidate)
                ) THEN
                    candidate := candidate || ' ' || duplicate.id;
                END IF;
                UPDATE teams SET name = candidate WHERE id = duplicate.id;
            END LOOP;
        END $$
        """
    )
    op.execute(
        """
        UPDATE teams
        SET branch = 'mixto', category = 'u12'
        WHERE LOWER(BTRIM(category)) = 'u12'
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX teams_normalized_name_branch_category_key
        ON teams (LOWER(BTRIM(name)), branch, category)
        """
    )
    op.create_check_constraint(
        "teams_u12_mixed_branch_check",
        "teams",
        "LOWER(BTRIM(category)) <> 'u12' OR LOWER(BTRIM(branch)) = 'mixto'",
    )


def downgrade() -> None:
    """Remove the rule; normalized data remains mixed to avoid guessing history."""
    op.drop_constraint(
        "teams_u12_mixed_branch_check",
        "teams",
        type_="check",
    )
