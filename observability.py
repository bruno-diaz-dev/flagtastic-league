"""Production observability without collecting league-member personal data."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
import re
import sys
from time import perf_counter
from uuid import uuid4

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from starlette.datastructures import Headers, MutableHeaders


LOGGER_NAME = "flagtastic"
SAFE_LOG_FIELDS = (
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "error_type",
    "sentry_enabled",
)
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
HEALTH_PATHS = {"/live", "/ready"}
SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "curp",
    "email",
    "password",
    "password_hash",
    "profile_photo_data",
    "secret",
    "session_token",
    "set-cookie",
    "team_logo_data",
    "token",
    "token_hash",
    "x-api-key",
}
NORMALIZED_SENSITIVE_KEYS = {item.replace("_", "-") for item in SENSITIVE_KEYS}
TEXT_REDACTIONS = (
    (re.compile(r"postgres(?:ql)?://[^\s]+", re.IGNORECASE), "[redacted-database-url]"),
    (
        re.compile(r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b", re.IGNORECASE),
        "[redacted-curp]",
    ),
    (
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
        "[redacted-email]",
    ),
    (
        re.compile(
            r"\b(password|secret|token|cookie|authorization)\b"
            r"(\s*[=:]\s*)([^\s,;]+)",
            re.IGNORECASE,
        ),
        r"\1\2[redacted]",
    ),
)


def application_environment() -> str:
    """Return a stable environment label for logs and Sentry events."""
    return os.getenv("APP_ENV") or os.getenv("VERCEL_ENV") or "development"


def application_release() -> str | None:
    """Identify the immutable deployment when the hosting platform provides it."""
    return os.getenv("SENTRY_RELEASE") or os.getenv("VERCEL_GIT_COMMIT_SHA")


class JsonLogFormatter(logging.Formatter):
    """Serialize an explicit allowlist of operational fields as one JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
            "environment": application_environment(),
        }
        release = application_release()
        if release:
            payload["release"] = release
        for field in SAFE_LOG_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=True, default=str)


def redact_text(value: str) -> str:
    """Remove common credentials and league identity values from free text."""
    redacted = value
    for pattern, replacement in TEXT_REDACTIONS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def _redact_value(value, key: str | None = None):
    """Recursively sanitize fields that Sentry integrations may add."""
    if key and key.lower().replace("_", "-") in NORMALIZED_SENSITIVE_KEYS:
        return "[redacted]"
    if isinstance(value, dict):
        return {
            item_key: _redact_value(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    if isinstance(value, str):
        return redact_text(value)
    return value


def configure_logging() -> logging.Logger:
    """Configure the application logger once while leaving server logs intact."""
    logger = logging.getLogger(LOGGER_NAME)
    requested_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, requested_level, logging.INFO))
    logger.propagate = False
    if not any(getattr(handler, "flagtastic_json", False) for handler in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonLogFormatter())
        handler.flagtastic_json = True
        logger.addHandler(handler)
    return logger


def _traces_sample_rate() -> float:
    """Read a bounded trace sample rate without breaking application startup."""
    try:
        value = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    except ValueError:
        return 0.1
    return min(max(value, 0.0), 1.0)


def scrub_sentry_event(event, _hint):
    """Remove request material that could contain credentials or player data."""
    request = event.get("request")
    if isinstance(request, dict):
        for key in ("cookies", "data", "query_string"):
            request.pop(key, None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            request["headers"] = {
                key: value
                for key, value in headers.items()
                if key.lower() not in {
                    "authorization", "cookie", "set-cookie", "x-api-key"
                }
            }
        elif isinstance(headers, list):
            request["headers"] = [
                item for item in headers
                if not item or str(item[0]).lower() not in {
                    "authorization", "cookie", "set-cookie", "x-api-key"
                }
            ]
    event.pop("user", None)
    return _redact_value(event)


def scrub_sentry_log(log, _hint):
    """Apply the same field and free-text redaction to Sentry log records."""
    return _redact_value(log)


def initialize_sentry() -> bool:
    """Enable Sentry only when a deployment supplies a DSN."""
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return False
    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=application_environment(),
            release=application_release(),
            send_default_pii=False,
            include_local_variables=False,
            max_request_body_size="never",
            traces_sample_rate=_traces_sample_rate(),
            enable_logs=True,
            before_send=scrub_sentry_event,
            before_send_transaction=scrub_sentry_event,
            before_send_log=scrub_sentry_log,
            integrations=[FastApiIntegration(transaction_style="endpoint")],
        )
    except Exception as error:
        logging.getLogger(LOGGER_NAME).warning(
            "application.sentry.configuration_failed",
            extra={"error_type": type(error).__name__},
        )
        return False
    return True


def configure_observability() -> logging.Logger:
    """Initialize local structured logs and optional hosted telemetry."""
    logger = configure_logging()
    sentry_enabled = initialize_sentry()
    logger.info(
        "application.observability.configured",
        extra={"sentry_enabled": sentry_enabled},
    )
    return logger


def _request_id(headers: Headers) -> str:
    """Reuse a safe upstream correlation id or generate a local one."""
    candidate = headers.get("x-request-id") or headers.get("x-vercel-id")
    if candidate and REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return uuid4().hex


class RequestObservabilityMiddleware:
    """Add correlation headers and one privacy-safe completion log per request."""

    def __init__(self, app, logger: logging.Logger | None = None):
        self.app = app
        self.logger = logger or logging.getLogger(LOGGER_NAME)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = _request_id(headers)
        method = scope.get("method", "")
        path = scope.get("path", "")
        started_at = perf_counter()
        status_code = 500

        async def send_with_request_id(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message).append("x-request-id", request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception as error:
            self.logger.exception(
                "request.failed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": 500,
                    "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                    "error_type": type(error).__name__,
                },
            )
            raise

        if path in HEALTH_PATHS and status_code < 400:
            return
        level = logging.ERROR if status_code >= 500 else logging.INFO
        self.logger.log(
            level,
            "request.completed",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            },
        )
