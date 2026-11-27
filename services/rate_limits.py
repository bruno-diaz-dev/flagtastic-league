"""Rate limits for sign-in, registration and password recovery.

Counters live in PostgreSQL because every Vercel function instance must see
the same totals. Only SHA-256 hashes of the client IP or email are stored.
"""

import hashlib
import os

from fastapi import HTTPException, Request

from repositories.rate_limits import current_attempts, record_attempt


# bucket: (maximum attempts, window in seconds)
LIMITS = {
    # Every sign-in attempt from one client address (web and mobile).
    "login_ip": (60, 5 * 60),
    # Failed sign-ins for one account, wherever they come from.
    "login_email_failures": (10, 15 * 60),
    "register_ip": (10, 60 * 60),
    "forgot_ip": (10, 15 * 60),
    # Reset emails for one account; over the limit nothing is sent, and the
    # response stays identical so it does not reveal whether the email exists.
    "forgot_email": (5, 60 * 60),
    "reset_ip": (20, 15 * 60),
}
TOO_MANY_ATTEMPTS = "Demasiados intentos. Espera unos minutos e intenta de nuevo."


def rate_limits_enabled():
    """Off in the test suite (many logins from one address) or by explicit opt-out."""
    if os.getenv("APP_ENV", "").lower() == "test":
        return False
    return os.getenv("AUTH_RATE_LIMITS", "true").lower() != "false"


def client_address(request: Request):
    """The caller's IP. On Vercel these headers are set by the platform."""
    for header in ("x-vercel-forwarded-for", "x-real-ip", "x-forwarded-for"):
        value = request.headers.get(header)
        if value:
            return value.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _key_hash(bucket, value):
    normalized = (value or "").strip().lower()
    return hashlib.sha256(f"{bucket}:{normalized}".encode("utf-8")).hexdigest()


def _too_many(retry_after):
    return HTTPException(
        status_code=429,
        detail=TOO_MANY_ATTEMPTS,
        headers={"Retry-After": str(max(1, int(retry_after)))}
    )


def count_attempt(bucket, value):
    """Count an attempt and reject it with 429 once the bucket is over its limit."""
    if not rate_limits_enabled():
        return
    limit, window = LIMITS[bucket]
    result = record_attempt(bucket, _key_hash(bucket, value), window)
    if result is not None and result[0] > limit:
        raise _too_many(result[1])


def is_over_limit(bucket, value):
    """Count an attempt and report, without raising, whether it is over the limit."""
    if not rate_limits_enabled():
        return False
    limit, window = LIMITS[bucket]
    result = record_attempt(bucket, _key_hash(bucket, value), window)
    return result is not None and result[0] > limit


def reject_if_blocked(bucket, value):
    """Reject with 429 while earlier attempts already reached the limit; counts nothing."""
    if not rate_limits_enabled():
        return
    limit, window = LIMITS[bucket]
    attempts, retry_after = current_attempts(bucket, _key_hash(bucket, value), window)
    if attempts >= limit:
        raise _too_many(retry_after)


def record_failure(bucket, value):
    """Count a failed attempt without rejecting the current request."""
    if not rate_limits_enabled():
        return
    _limit, window = LIMITS[bucket]
    record_attempt(bucket, _key_hash(bucket, value), window)
