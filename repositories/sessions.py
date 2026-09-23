import hashlib
import secrets

from datetime import datetime, timedelta, timezone

from database import get_connection

SESSION_DURATION = timedelta(hours=12)

def hash_session_token(token):
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

def create_session(user_id):
    token = secrets.token_urlsafe(32)
    token_hash = hash_session_token(token)

    expires_at = (
        datetime.now(timezone.utc)
        + SESSION_DURATION
    )

    connection = get_connection()

    try:
        created_session = connection.execute(
            """
            INSERT INTO sessions (
                user_id,
                token_hash,
                expires_at
            )
            VALUES (%s, %s, %s)
            RETURNING
                id,
                user_id,
                expires_at,
                created_at,
                revoked_at
            """,
            (
                user_id,
                token_hash,
                expires_at,
            )
        ).fetchone()

        connection.commit()

        session = dict(created_session)
        session["token"] = token

        return session

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def get_active_session(token):
    token_hash = hash_session_token(token)
    connection = get_connection()

    try:
        session = connection.execute(
            """
            SELECT
                id,
                user_id,
                expires_at,
                created_at,
                revoked_at
            FROM sessions
            WHERE token_hash = %s
                AND revoked_at IS NULL
                AND expires_at > NOW()
            """,
            (token_hash,)
        ).fetchone()

        if session is None:
            return None
        
        return dict(session)

    finally:
        connection.close()

def revoke_session(token):
    token_hash= hash_session_token(token)
    connection = get_connection()

    try:
        revoked_session = connection.execute(
            """
            UPDATE sessions
            SET revoked_at = NOW()
            WHERE token_hash = %s
                AND revoked_at IS NULL
            RETURNING id
            """,
            (token_hash,)
        ).fetchone()

        connection.commit()
        
        return revoked_session is not None
    
    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()