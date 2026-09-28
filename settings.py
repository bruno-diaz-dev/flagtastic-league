"""Small environment-backed settings shared across HTTP boundaries."""

import os


SESSION_COOKIE_NAME = "flagtastic_session"
SESSION_MAX_AGE_SECONDS = 12 * 60 * 60
PROFILE_PHOTO_MAX_BYTES = 5 * 1024 * 1024
TEAM_LOGO_MAX_BYTES = 5 * 1024 * 1024
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
PASSWORD_RESET_FROM_EMAIL = os.getenv("PASSWORD_RESET_FROM_EMAIL", "")


def session_cookie_is_secure():
    """Return whether session cookies must only travel over HTTPS."""
    return os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
