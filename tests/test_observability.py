"""Observability contracts for correlation, health checks, and data hygiene."""

import json
import logging

from fastapi.testclient import TestClient

import main
from main import app
from observability import (
    JsonLogFormatter,
    initialize_sentry,
    redact_text,
    scrub_sentry_event,
    scrub_sentry_log,
)


client = TestClient(app)


def test_liveness_has_request_id_and_disables_caching():
    response = client.get("/live", headers={"x-request-id": "release-check-123"})

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    assert response.headers["x-request-id"] == "release-check-123"
    assert response.headers["cache-control"] == "no-store"


def test_invalid_incoming_request_id_is_replaced():
    response = client.get("/live", headers={"x-request-id": "invalid id value"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "invalid id value"
    assert len(response.headers["x-request-id"]) == 32


def test_readiness_checks_the_database():
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    assert response.headers["cache-control"] == "no-store"


def test_readiness_hides_database_error_details(monkeypatch):
    def fail_to_connect():
        raise RuntimeError("postgresql://user:secret@example.test/private")

    monkeypatch.setattr(main, "get_connection", fail_to_connect)
    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "secret" not in response.text


def test_json_logs_only_include_approved_context():
    record = logging.LogRecord(
        name="flagtastic",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="auth.checked",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-1"
    record.password = "must-not-appear"
    record.curp = "must-not-appear"
    record.email = "must-not-appear@example.test"

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["event"] == "auth.checked"
    assert payload["request_id"] == "request-1"
    assert "password" not in payload
    assert "curp" not in payload
    assert "email" not in payload


def test_free_text_redacts_identity_and_credentials():
    text = (
        "duplicate email=player@example.test curp DIBB961215HASZRR00 "
        "password=supersecret postgresql://user:secret@example.test/private"
    )

    redacted = redact_text(text)

    assert "player@example.test" not in redacted
    assert "DIBB961215HASZRR00" not in redacted
    assert "supersecret" not in redacted
    assert "postgresql://" not in redacted


def test_sentry_event_scrubber_removes_request_and_user_data():
    event = {
        "request": {
            "data": {"password": "secret"},
            "cookies": {"flagtastic_session": "secret"},
            "query_string": "token=secret",
            "headers": {
                "Cookie": "secret",
                "Authorization": "Bearer secret",
                "Accept": "application/json",
            },
        },
        "exception": {
            "values": [{"value": "duplicate email player@example.test"}]
        },
        "user": {"email": "player@example.test"},
    }

    scrubbed = scrub_sentry_event(event, None)

    assert "data" not in scrubbed["request"]
    assert "cookies" not in scrubbed["request"]
    assert "query_string" not in scrubbed["request"]
    assert scrubbed["request"]["headers"] == {"Accept": "application/json"}
    assert "player@example.test" not in scrubbed["exception"]["values"][0]["value"]
    assert "user" not in scrubbed


def test_sentry_log_scrubber_redacts_body_and_attributes():
    log = {
        "body": "failed for player@example.test",
        "attributes": {
            "curp": "DIBB961215HASZRR00",
            "request_id": "safe-request-id",
        },
    }

    scrubbed = scrub_sentry_log(log, None)

    assert "player@example.test" not in scrubbed["body"]
    assert scrubbed["attributes"]["curp"] == "[redacted]"
    assert scrubbed["attributes"]["request_id"] == "safe-request-id"


def test_sentry_is_optional_and_privacy_safe(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.test/1")
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.25")
    captured = {}

    def fake_init(**options):
        captured.update(options)

    monkeypatch.setattr("observability.sentry_sdk.init", fake_init)

    assert initialize_sentry() is True
    assert captured["send_default_pii"] is False
    assert captured["include_local_variables"] is False
    assert captured["max_request_body_size"] == "never"
    assert captured["traces_sample_rate"] == 0.25
    assert captured["enable_logs"] is True
    assert captured["before_send_transaction"] is scrub_sentry_event
    assert captured["before_send_log"] is scrub_sentry_log


def test_invalid_sentry_configuration_does_not_break_startup(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "invalid")

    def fail_to_initialize(**_options):
        raise ValueError("invalid DSN")

    monkeypatch.setattr("observability.sentry_sdk.init", fail_to_initialize)

    assert initialize_sentry() is False
