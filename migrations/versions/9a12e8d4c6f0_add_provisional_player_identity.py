"""Support explicit provisional documents and private birth dates.

Revision ID: 9a12e8d4c6f0
Revises: eb90fd6b4af8
"""

from alembic import op

revision = "9a12e8d4c6f0"
down_revision = "eb90fd6b4af8"
branch_labels = None
depends_on = None


def upgrade():
    """Add compatible fields; tolerate a verified out-of-band deployment."""
    op.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS identity_type TEXT NOT NULL DEFAULT 'curp'")
    op.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS birth_date DATE")
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'players_identity_type_check'
                  AND conrelid = 'players'::regclass
            ) THEN
                ALTER TABLE players ADD CONSTRAINT players_identity_type_check
                    CHECK (identity_type IN ('curp', 'provisional'));
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'players_provisional_birth_date_check'
                  AND conrelid = 'players'::regclass
            ) THEN
                ALTER TABLE players ADD CONSTRAINT players_provisional_birth_date_check
                    CHECK (identity_type <> 'provisional' OR (
                        birth_date IS NOT NULL AND char_length(curp) BETWEEN 1 AND 17
                    ));
            END IF;
        END $$;
    """)


def downgrade():
    op.drop_constraint("players_provisional_birth_date_check", "players", type_="check")
    op.drop_constraint("players_identity_type_check", "players", type_="check")
    op.drop_column("players", "birth_date")
    op.drop_column("players", "identity_type")
