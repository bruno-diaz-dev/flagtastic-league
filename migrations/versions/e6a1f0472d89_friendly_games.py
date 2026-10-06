"""Distinguish friendly fixtures and invited team identities."""
from alembic import op

revision = "e6a1f0472d89"
down_revision = "d5f9a1432c76"
branch_labels = None
depends_on = None

SCHEMA = """
ALTER TABLE teams ADD COLUMN is_guest BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE games ADD COLUMN is_friendly BOOLEAN NOT NULL DEFAULT FALSE;
"""

def upgrade():
    op.execute(SCHEMA)

def downgrade():
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM games WHERE is_friendly)
            OR EXISTS (SELECT 1 FROM teams WHERE is_guest) THEN
            RAISE EXCEPTION 'Recorded friendlies prevent downgrade; use a forward migration';
        END IF;
    END $$;
    ALTER TABLE games DROP COLUMN is_friendly;
    ALTER TABLE teams DROP COLUMN is_guest;
    """)
