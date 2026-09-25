"""Small environment-backed settings shared across HTTP boundaries."""

import os


SESSION_COOKIE_NAME = "flagtastic_session"
SESSION_MAX_AGE_SECONDS = 12 * 60 * 60
PROFILE_PHOTO_MAX_BYTES = 5 * 1024 * 1024
TEAM_LOGO_MAX_BYTES = 5 * 1024 * 1024


def session_cookie_is_secure():
    """Return whether session cookies must only travel over HTTPS."""
    return os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
