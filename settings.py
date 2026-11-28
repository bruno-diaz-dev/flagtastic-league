"""Small environment-backed settings shared across HTTP boundaries."""

import os


SESSION_COOKIE_NAME = "flagtastic_session"
SESSION_MAX_AGE_SECONDS = 12 * 60 * 60
# Vercel rejects request bodies above 4.5 MB before the app runs, with a
# plain-text error. Keeping single-file uploads at 4 MiB means oversized files
# always get the application's own message instead.
UPLOAD_MAX_BYTES = 4 * 1024 * 1024
UPLOAD_MAX_LABEL = "4 MB"
PROFILE_PHOTO_MAX_BYTES = UPLOAD_MAX_BYTES
TEAM_LOGO_MAX_BYTES = UPLOAD_MAX_BYTES
ROSTER_IMPORT_MAX_BYTES = UPLOAD_MAX_BYTES
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
PASSWORD_RESET_FROM_EMAIL = os.getenv("PASSWORD_RESET_FROM_EMAIL", "")


def session_cookie_is_secure():
    """Return whether session cookies must only travel over HTTPS."""
    return os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
