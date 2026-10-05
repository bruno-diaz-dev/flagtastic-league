"""Persist logo hashes so team reads never re-hash large image blobs.

Revision ID: c4e8f0321b65
Revises: b3d7e9210a54
"""
from alembic import op

revision = "c4e8f0321b65"
down_revision = "b3d7e9210a54"
branch_labels = None
depends_on = None

SCHEMA = "ALTER TABLE teams ADD COLUMN IF NOT EXISTS logo_version TEXT GENERATED ALWAYS AS (md5(logo_data)) STORED;"


def upgrade():
    op.execute(SCHEMA)


def downgrade():
    op.execute("ALTER TABLE teams DROP COLUMN IF EXISTS logo_version")
