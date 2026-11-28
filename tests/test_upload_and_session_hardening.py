"""Uploads are cleaned and bounded; password changes end other sessions."""

import asyncio
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from PIL import Image

from main import app
from models import UserCreate
from repositories.sessions import create_session
from repositories.users import create_user
from services import profile_photos
from services.logo_thumbnails import thumbnail_logo
from services.roster_import import RosterImportError, parse_roster_file
from tests.image_samples import jpeg_with_exif, png_bytes


client = TestClient(app, base_url="https://testserver")


def upload(content, filename="photo.jpg"):
    return UploadFile(file=BytesIO(content), filename=filename)


def test_profile_photo_is_reencoded_without_exif_metadata():
    original = jpeg_with_exif(size=(8, 6))
    with Image.open(BytesIO(original)) as image:
        assert image.getexif().get(0x010F) == "PhoneMaker"

    saved = asyncio.run(profile_photos.save_profile_photo(upload(original)))

    assert saved["media_type"] == "image/jpeg"
    with Image.open(BytesIO(saved["content"])) as image:
        assert image.format == "JPEG"
        exif = image.getexif()
        assert len(exif) == 0
        assert "exif" not in image.info
        # The camera orientation (rotate 90 degrees) is applied to the pixels.
        assert image.size == (6, 8)


def test_profile_photo_is_bounded_on_its_longest_side():
    saved = asyncio.run(profile_photos.save_profile_photo(
        upload(png_bytes(size=(3200, 100)), "wide.png")
    ))
    with Image.open(BytesIO(saved["content"])) as image:
        assert image.size == (profile_photos.PROFILE_PHOTO_MAX_SIDE, 50)


def test_profile_photo_with_a_valid_signature_but_no_image_is_rejected():
    with pytest.raises(HTTPException) as error:
        asyncio.run(profile_photos.save_profile_photo(
            upload(b"\x89PNG\r\n\x1a\nnot-really-a-png", "fake.png")
        ))
    assert error.value.status_code == 415


def test_images_declaring_too_many_pixels_are_rejected_before_decoding(monkeypatch):
    monkeypatch.setattr(profile_photos, "MAX_IMAGE_PIXELS", 100)
    big = png_bytes(size=(20, 20))
    with pytest.raises(HTTPException) as photo_error:
        asyncio.run(profile_photos.save_profile_photo(upload(big, "big.png")))
    with pytest.raises(HTTPException) as logo_error:
        asyncio.run(profile_photos.save_team_logo(upload(big, "big.png")))
    assert photo_error.value.status_code == 413
    assert logo_error.value.status_code == 413


def test_oversized_stored_logo_is_served_unchanged_instead_of_decoded(monkeypatch):
    monkeypatch.setattr("services.logo_thumbnails.MAX_IMAGE_PIXELS", 100)
    big = png_bytes(size=(20, 20))
    content, media_type = thumbnail_logo(big, "image/png", 64)
    assert content == big
    assert media_type == "image/png"


def test_xlsx_roster_stops_at_the_player_limit_without_reading_every_row():
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["nombre", "curp", "numero"])
    for index in range(150):
        sheet.append([f"Jugador {index}", f"JUGA900101HAS{index:05d}", index])
    output = BytesIO()
    workbook.save(output)

    with pytest.raises(RosterImportError, match="mas de 100 jugadores"):
        parse_roster_file("roster.xlsx", output.getvalue())


def test_jersey_numbers_and_names_have_upper_bounds():
    from pydantic import ValidationError
    from models import PlayerCreate, TeamCreate, TeamMembershipCreate

    with pytest.raises(ValidationError):
        TeamMembershipCreate(jersey_number=10_000_000_000)
    with pytest.raises(ValidationError):
        PlayerCreate(name="A" * 121, curp="DIBB961215HASXXX00", age=29, jersey_number=1)
    with pytest.raises(ValidationError):
        TeamCreate(name="T" * 121, branch="varonil", category="libre")


def test_responses_carry_security_headers():
    response = client.get("/live")
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["content-security-policy"] == "frame-ancestors 'none'"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"


def test_changing_the_password_signs_out_every_other_session():
    app.dependency_overrides.clear()
    email = f"rotate-{uuid4().hex[:8]}@example.test"
    user = create_user(UserCreate(email=email, name="Rotate", password="oldsecret", role="referee"))
    other_device = create_session(user["id"])

    client.cookies.clear()
    assert client.post("/api/auth/login", json={"email": email, "password": "oldsecret"}).status_code == 200
    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": "oldsecret", "new_password": "newsecret1"}
    )

    assert changed.status_code == 204
    # The session that changed the password stays signed in...
    assert client.get("/api/auth/me").status_code == 200
    # ...and a token issued elsewhere (another browser, the mobile app) is revoked.
    # A Bearer header takes precedence over the browser cookie.
    other = client.get("/api/auth/me", headers={"Authorization": f"Bearer {other_device['token']}"})
    assert other.status_code == 401


def test_mobile_token_can_change_the_password():
    app.dependency_overrides.clear()
    email = f"mobile-{uuid4().hex[:8]}@example.test"
    user = create_user(UserCreate(email=email, name="Mobile", password="oldsecret", role="referee"))
    token = create_session(user["id"])["token"]
    client.cookies.clear()

    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": "oldsecret", "new_password": "newsecret1"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert changed.status_code == 204
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_unknown_email_login_still_hashes_the_password(monkeypatch):
    from services import auth

    calls = []
    real_verify = auth.verify_password
    monkeypatch.setattr(auth, "verify_password", lambda *args: calls.append(args) or real_verify(*args))
    assert auth.authenticate_user(f"nobody-{uuid4().hex}@example.test", "whatever1") is None
    assert len(calls) == 1
