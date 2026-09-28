"""Single-use password reset token persistence."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from database import get_connection
from repositories.users import hash_password


RESET_DURATION = timedelta(minutes=30)
RESET_COOLDOWN = timedelta(seconds=60)


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset(email):
    """Return a raw token once for an active account, subject to cooldown."""
    connection = get_connection()
    try:
        user = connection.execute(
            "SELECT id, email FROM users WHERE email = %s AND status = 'active'",
            (email.strip().lower(),),
        ).fetchone()
        if user is None:
            return None

        recent = connection.execute(
            """
            SELECT 1 FROM password_reset_tokens
            WHERE user_id = %s AND created_at > %s
            LIMIT 1
            """,
            (user["id"], datetime.now(timezone.utc) - RESET_COOLDOWN),
        ).fetchone()
        if recent is not None:
            return None

        token = secrets.token_urlsafe(32)
        connection.execute(
            """
            UPDATE password_reset_tokens SET used_at = NOW()
            WHERE user_id = %s AND used_at IS NULL
            """,
            (user["id"],),
        )
        connection.execute(
            """
            INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            """,
            (
                user["id"],
                _hash_token(token),
                datetime.now(timezone.utc) + RESET_DURATION,
            ),
        )
        connection.commit()
        return {"email": user["email"], "token": token}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def consume_password_reset(token, new_password):
    """Atomically consume a valid token, replace the password, and log out."""
    connection = get_connection()
    try:
        reset = connection.execute(
            """
            SELECT id, user_id FROM password_reset_tokens
            WHERE token_hash = %s AND used_at IS NULL AND expires_at > NOW()
            FOR UPDATE
            """,
            (_hash_token(token),),
        ).fetchone()
        if reset is None:
            return False

        connection.execute(
            """
            UPDATE users
            SET password_hash = %s, must_change_password = false
            WHERE id = %s
            """,
            (hash_password(new_password), reset["user_id"]),
        )
        connection.execute(
            "UPDATE password_reset_tokens SET used_at = NOW() WHERE id = %s",
            (reset["id"],),
        )
        connection.execute(
            """
            UPDATE sessions SET revoked_at = NOW()
            WHERE user_id = %s AND revoked_at IS NULL
            """,
            (reset["user_id"],),
        )
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
