"""Unit tests for referee-role image extraction before database writes."""

from io import BytesIO

from PIL import Image

from services.referee_schedule_ocr import parse_referee_schedule_image


def test_schedule_ocr_matches_game_referee_and_field(monkeypatch):
    image = Image.new("RGB", (40, 40), "white")
    content = BytesIO()
    image.save(content, format="PNG")
    monkeypatch.setattr(
        "services.referee_schedule_ocr.pytesseract.image_to_string",
        lambda image, config: "Campo 5 Tigres vs Ravens Arbitro Central"
    )
    games = [{
        "id": 44,
        "week": 3,
        "home_team": {"name": "Tigres"},
        "away_team": {"name": "Ravens"}
    }]
    referees = [{"id": 9, "name": "Arbitro Central"}]

    parsed = parse_referee_schedule_image(content.getvalue(), games, referees)

    assert parsed["proposals"] == [{
        "game_id": 44,
        "game_label": "J3: Tigres vs Ravens",
        "field_number": 5,
        "officials": [{
            "user_id": 9,
            "name": "Arbitro Central",
            "position": "referee"
        }],
        "source_text": "Campo 5 Tigres vs Ravens Arbitro Central"
    }]
