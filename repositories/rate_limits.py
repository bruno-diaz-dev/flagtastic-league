"""Fixed-window attempt counters stored in auth_rate_limits."""

import logging
import random

from psycopg.errors import UndefinedTable

from database import get_connection


logger = logging.getLogger("flagtastic.rate_limits")

# Rows older than this are removed now and then; no limit window is longer.
RETENTION = "1 day"
CLEANUP_PROBABILITY = 0.01
WINDOW_START_SQL = "to_timestamp(floor(extract(epoch FROM now()) / %(window)s) * %(window)s)"
RETRY_AFTER_SQL = (
    "GREATEST(1, CEIL(extract(epoch FROM window_start) + %(window)s "
    "- extract(epoch FROM now())))::int"
)


def _table_missing(connection, error):
    # Deployed before its migration ran: never block sign-in because of it.
    connection.rollback()
    logger.warning("rate_limits.table_missing", extra={"error_type": type(error).__name__})


def record_attempt(bucket, key_hash, window_seconds):
    """Count one attempt in the current window.

    Returns ``(attempts, retry_after_seconds)`` including this attempt, or
    ``None`` when the table does not exist yet.
    """
    parameters = {"bucket": bucket, "key": key_hash, "window": window_seconds}
    connection = get_connection()
    try:
        row = connection.execute(
            f"""
            INSERT INTO auth_rate_limits (bucket, key_hash, window_start, attempts)
            VALUES (%(bucket)s, %(key)s, {WINDOW_START_SQL}, 1)
            ON CONFLICT (bucket, key_hash, window_start)
            DO UPDATE SET attempts = auth_rate_limits.attempts + 1
            RETURNING attempts, {RETRY_AFTER_SQL} AS retry_after
            """,
            parameters
        ).fetchone()
        if random.random() < CLEANUP_PROBABILITY:
            connection.execute(
                f"DELETE FROM auth_rate_limits WHERE window_start < now() - interval '{RETENTION}'"
            )
        connection.commit()
        return row["attempts"], row["retry_after"]
    except UndefinedTable as error:
        _table_missing(connection, error)
        return None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def current_attempts(bucket, key_hash, window_seconds):
    """Return ``(attempts, retry_after_seconds)`` in the current window without counting."""
    parameters = {"bucket": bucket, "key": key_hash, "window": window_seconds}
    connection = get_connection()
    try:
        row = connection.execute(
            f"""
            SELECT attempts, {RETRY_AFTER_SQL} AS retry_after
            FROM auth_rate_limits
            WHERE bucket = %(bucket)s AND key_hash = %(key)s
              AND window_start = {WINDOW_START_SQL}
            """,
            parameters
        ).fetchone()
        return (row["attempts"], row["retry_after"]) if row is not None else (0, 0)
    except UndefinedTable as error:
        _table_missing(connection, error)
        return (0, 0)
    finally:
        connection.close()
