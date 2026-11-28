"""Operational guards: upload limits, database timeout, mock-data scripts."""

import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

import database
from scripts.data_target_guard import require_non_production_target
from services.profile_photos import save_profile_photo, save_team_logo
from settings import UPLOAD_MAX_BYTES


def test_single_file_uploads_stay_below_the_vercel_request_cap():
    # Vercel rejects bodies over 4.5 MB with a plain-text error.
    assert UPLOAD_MAX_BYTES < 4_500_000
    oversized = b"\x89PNG\r\n\x1a\n" + b"0" * UPLOAD_MAX_BYTES
    for save in (save_profile_photo, save_team_logo):
        with pytest.raises(HTTPException) as error:
            asyncio.run(save(UploadFile(file=BytesIO(oversized), filename="big.png")))
        assert error.value.status_code == 413
        assert "4 MB" in error.value.detail


def test_database_connections_fail_fast(monkeypatch):
    calls = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://example.invalid/db")
    monkeypatch.delenv("DATABASE_CONNECT_TIMEOUT", raising=False)
    monkeypatch.setattr(database.psycopg, "connect", lambda *args, **kwargs: calls.append(kwargs))
    database.get_connection()
    assert calls[0]["connect_timeout"] == database.DEFAULT_CONNECT_TIMEOUT_SECONDS


@pytest.mark.parametrize("target", ["", "production", "prod"])
def test_mock_data_scripts_refuse_an_unconfirmed_target(monkeypatch, target):
    monkeypatch.setenv("FLAGTASTIC_DATA_TARGET", target)
    with pytest.raises(SystemExit):
        require_non_production_target("balance_mock_games")


@pytest.mark.parametrize("target", ["local", "Preview", "test"])
def test_mock_data_scripts_run_against_a_confirmed_target(monkeypatch, target):
    monkeypatch.setenv("FLAGTASTIC_DATA_TARGET", target)
    require_non_production_target("balance_mock_games")
