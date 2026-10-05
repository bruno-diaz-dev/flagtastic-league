"""Optional field locations for preview visual coverage."""
from alembic import op
revision = "e6a0b2548c17"
down_revision = "d5f9a1432c76"
branch_labels = None
depends_on = None
SCHEMA = """
ALTER TABLE game_live_events ADD COLUMN field_location jsonb;
ALTER TABLE game_live_events ADD CONSTRAINT game_live_events_field_location_check CHECK (
 field_location IS NULL OR (
 kind IN ('pass_complete','pass_incomplete','passing_touchdown','touchdown','interception')
 AND jsonb_typeof(field_location) = 'object'
 AND field_location ?& ARRAY['start_x','start_y','end_x','end_y']
 AND field_location - ARRAY['start_x','start_y','end_x','end_y'] = '{}'::jsonb
 AND (field_location->>'start_x') ~ '^(100|[0-9]{1,2})$'
 AND (field_location->>'start_y') ~ '^(100|[0-9]{1,2})$'
 AND (field_location->>'end_x') ~ '^(100|[0-9]{1,2})$'
 AND (field_location->>'end_y') ~ '^(100|[0-9]{1,2})$'
 AND jsonb_typeof(field_location->'start_x') = 'number'
 AND jsonb_typeof(field_location->'start_y') = 'number'
 AND jsonb_typeof(field_location->'end_x') = 'number'
 AND jsonb_typeof(field_location->'end_y') = 'number'
 ));
"""
def upgrade():
    op.execute(SCHEMA)
def downgrade():
    op.execute("ALTER TABLE game_live_events DROP COLUMN field_location")
