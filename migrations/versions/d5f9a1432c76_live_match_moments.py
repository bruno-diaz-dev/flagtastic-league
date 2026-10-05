"""Add neutral match moments without altering historical attendance records."""
from alembic import op
revision = "d5f9a1432c76"
down_revision = "c4e8f0321b65"
branch_labels = None
depends_on = None
SCHEMA = """
ALTER TABLE game_live_events ALTER COLUMN team_id DROP NOT NULL;
ALTER TABLE game_live_events DROP CONSTRAINT game_live_events_kind_check;
ALTER TABLE game_live_events ADD CONSTRAINT game_live_events_kind_check CHECK (kind IN ('pass_complete','pass_incomplete','passing_touchdown','touchdown','extra_one','extra_two','safety','sack','flag','interception','attendance','note','halftime','two_minute_warning'));
ALTER TABLE game_live_events ADD CONSTRAINT game_live_events_moment_identity_check CHECK (
    (kind IN ('halftime','two_minute_warning') AND team_id IS NULL AND player_id IS NULL AND receiver_id IS NULL)
    OR (kind NOT IN ('halftime','two_minute_warning') AND team_id IS NOT NULL)
);
"""
def upgrade():
    op.execute(SCHEMA)
def downgrade():
    raise RuntimeError("Match moments are retained for audit; forward migration required")
