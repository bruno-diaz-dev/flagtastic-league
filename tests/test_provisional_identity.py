"""Provisional documents keep a private birth date and a stable player ID."""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from database import get_connection
from main import app
from models import PlayerAccountCreate, PlayerCreate
from services.curp import age_from_birth_date


DOCUMENT = "TEST120728MBEXLT"
BIRTH_DATE = "2012-07-28"
PHOTO = b"\x89PNG\r\n\x1a\nprovisional-profile"


def payload(document=DOCUMENT, **changes):
    return {"name": "Test Player", "curp": document, "identity_type": "provisional", "birth_date": BIRTH_DATE, "jersey_number": 10, **changes}


def test_short_documents_require_explicit_type_and_birth_date():
    player = PlayerCreate(**payload())
    assert player.curp == DOCUMENT
    assert player.birth_date == date(2012, 7, 28)
    assert player.age == age_from_birth_date(player.birth_date)
    for changes in [{"identity_type": "curp"}, {"birth_date": None}, {"birth_date": date.today() + timedelta(days=1)}, {"curp": " "}, {"identity_type": "unknown"}]:
        with pytest.raises(ValidationError):
            PlayerCreate(**payload(**changes))
    with pytest.raises(ValidationError):
        PlayerAccountCreate(email="test@example.test", password="supersecret", name="Player", curp=DOCUMENT, age=14)


def test_explicit_birth_date_uses_completed_years():
    assert age_from_birth_date(date(2012, 7, 28), date(2026, 7, 27)) == 13
    assert age_from_birth_date(date(2012, 7, 28), date(2026, 7, 28)) == 14


def test_standard_curp_remains_default_and_overrides_untrusted_age():
    player = PlayerCreate(name="Player", curp="TEST120728MBEXLTA1", age=99, jersey_number=10)
    assert player.identity_type == "curp"
    assert player.age == age_from_birth_date(date(2012, 7, 28))


def test_manager_can_register_then_regularize_without_losing_membership():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8].upper()
        team = client.post("/api/teams", json={"name": f"provisional-{suffix}", "branch": "mixto", "category": "u14"}).json()
        document = f"TEMP{suffix}"
        created = client.post(f"/api/teams/{team['id']}/players", json=payload(document))
        assert created.status_code == 201
        player_id = created.json()["id"]
        private = client.get(f"/api/teams/{team['id']}/players/{player_id}/management").json()
        assert private["identity_type"] == "provisional"
        assert private["birth_date"] == BIRTH_DATE
        public = client.get(f"/api/teams/{team['id']}/players").json()[0]
        assert "birth_date" not in public and "curp" not in public and "identity_type" not in public
        mismatch = client.post(f"/api/teams/{team['id']}/players", json=payload(document, birth_date="2011-07-28"))
        assert mismatch.status_code == 409
        corrected = client.patch(f"/api/teams/{team['id']}/players/{player_id}", json=payload("TEST120728MBEXLTA1", identity_type="curp"))
        assert corrected.status_code == 200
        assert corrected.json()["id"] == player_id
        assert client.get(f"/api/teams/{team['id']}/players").json()[0]["id"] == player_id
        current = client.get(f"/api/teams/{team['id']}/players/{player_id}/management").json()
        assert current["identity_type"] == "curp"


def test_public_account_accepts_short_document_and_rejects_missing_birth_date():
    with TestClient(app, base_url="https://testserver") as client:
        document = f"TEMP{uuid4().hex[:8].upper()}"
        data = {"email": f"provisional-{uuid4().hex}@example.test", "password": "supersecret", "name": "Provisional Player", "curp": document, "identity_type": "provisional"}
        invalid = client.post("/api/auth/register/player", data=data, files={"photo": ("photo.png", PHOTO, "image/png")})
        assert invalid.status_code == 422
        data["birth_date"] = BIRTH_DATE
        valid = client.post("/api/auth/register/player", data=data, files={"photo": ("photo.png", PHOTO, "image/png")})
        assert valid.status_code == 201
        assert "birth_date" not in valid.json() and "curp" not in valid.json()
        connection = get_connection()
        saved = connection.execute("SELECT curp, identity_type, birth_date FROM players WHERE id = %s", (valid.json()["player_id"],)).fetchone()
        connection.close()
        assert saved["curp"] == document
        assert saved["birth_date"] == date(2012, 7, 28)
