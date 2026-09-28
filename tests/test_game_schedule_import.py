"""Tests for reviewed game imports from league schedule files."""

from io import BytesIO

from openpyxl import Workbook
from PIL import Image

from services.game_schedule_import import (
    parse_game_schedule_file,
    parse_game_schedule_image,
    parse_game_schedule_ocr_words,
)


TEAMS = [
    {"id": 1, "name": "Nomadas", "branch": "mixto", "category": "u8"},
    {"id": 2, "name": "Rancheras Flag", "branch": "mixto", "category": "u8"},
    {"id": 3, "name": "Ducks", "branch": "femenil", "category": "libre"},
    {"id": 4, "name": "Storms", "branch": "femenil", "category": "libre"},
]


def _calendar_file():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Calendario"
    sheet.append([None, "Semana 1"])
    sheet.append([None, "Hora", "Campo 1", None, "Campo 2", None])
    sheet.append([None, "12:00", "Nomadas U8", "Rancheras Flag U8"])
    sheet.append([None, "13:00", None, None, "Ducks Fem Libre", "Storms Fem Libre"])
    content = BytesIO()
    workbook.save(content)
    workbook.close()
    return content.getvalue()


def test_xlsx_calendar_layout_is_parsed_by_week_field_and_team_pair():
    result = parse_game_schedule_file("rol.xlsx", _calendar_file(), TEAMS)

    assert result["kind"] == "games"
    assert result["matched"] == 2
    assert result["unmatched"] == 0
    assert result["proposals"][0] == {
        "source_row": "Calendario!3",
        "week": 1,
        "field_number": 1,
        "start_time": "12:00",
        "home_team": "Nomadas U8",
        "away_team": "Rancheras Flag U8",
        "home_team_id": 1,
        "home_match": "Nomadas",
        "away_team_id": 2,
        "away_match": "Rancheras Flag",
        "ready": True,
    }
    assert result["proposals"][1]["field_number"] == 2


def test_csv_schedule_accepts_spanish_headers_and_marks_unknown_teams():
    content = (
        "jornada;campo;hora;local;visitante\n"
        "2;3;18:00;Ducks Fem Libre;Equipo inexistente\n"
    ).encode()

    result = parse_game_schedule_file("rol.csv", content, TEAMS)

    assert result["matched"] == 0
    assert result["unmatched"] == 1
    assert result["proposals"][0]["home_team_id"] == 3
    assert result["proposals"][0]["away_team_id"] is None
    assert result["proposals"][0]["ready"] is False


def test_image_schedule_is_read_as_games_not_referee_assignments(monkeypatch):
    image = Image.new("RGB", (1000, 500), "white")
    content = BytesIO()
    image.save(content, format="PNG")
    recognized_cells = iter([
        "Semana 5 Campo 1 12:00",
        "Nomadas U8",
        "Rancheras Flag U8",
    ])
    monkeypatch.setattr(
        "services.game_schedule_import.pytesseract.image_to_string",
        lambda *_args, **_kwargs: next(recognized_cells),
    )
    monkeypatch.setattr(
        "services.game_schedule_import.pytesseract.image_to_data",
        lambda *_args, **_kwargs: {
            "text": ["12:00"], "left": [5], "width": [40],
            "top": [300], "height": [20],
        },
    )

    result = parse_game_schedule_image(content.getvalue(), TEAMS)

    assert result["kind"] == "games"
    assert result["matched"] == 1
    assert result["proposals"][0]["week"] == 5
    assert result["proposals"][0]["home_team_id"] == 1
    assert "officials" not in result["proposals"][0]


def test_browser_ocr_words_are_grouped_into_schedule_cells():
    words = [
        {"text": "Semana", "left": 700, "top": 5, "width": 80, "height": 20},
        {"text": "1", "left": 790, "top": 5, "width": 10, "height": 20},
        {"text": "Campo", "left": 120, "top": 40, "width": 60, "height": 20},
        {"text": "1", "left": 185, "top": 40, "width": 10, "height": 20},
        {"text": "Campo", "left": 380, "top": 40, "width": 60, "height": 20},
        {"text": "2", "left": 445, "top": 40, "width": 10, "height": 20},
        {"text": "12:00", "left": 4, "top": 110, "width": 35, "height": 20},
        {"text": "Nomadas", "left": 75, "top": 110, "width": 70, "height": 20},
        {"text": "U8", "left": 150, "top": 110, "width": 25, "height": 20},
        {"text": "Rancheras", "left": 205, "top": 110, "width": 80, "height": 20},
        {"text": "Flag", "left": 290, "top": 110, "width": 35, "height": 20},
        {"text": "U8", "left": 330, "top": 110, "width": 25, "height": 20},
    ]

    result = parse_game_schedule_ocr_words(1000, 500, words, TEAMS)

    assert result["kind"] == "games"
    assert result["matched"] == 1
    assert result["unmatched"] == 0
    proposal = result["proposals"][0]
    assert proposal["week"] == 1
    assert proposal["field_number"] == 1
    assert proposal["start_time"] == "12:00"
    assert proposal["home_team_id"] == 1
    assert proposal["away_team_id"] == 2


def test_browser_ocr_recovers_week_and_field_count_when_labels_are_missed():
    words = [
        {"text": "1", "left": 780, "top": 8, "width": 12, "height": 18},
        {"text": "1", "left": 160, "top": 55, "width": 12, "height": 18},
        {"text": "2", "left": 430, "top": 55, "width": 12, "height": 18},
        {"text": "12:00", "left": 4, "top": 110, "width": 40, "height": 20},
        {"text": "Nomadas", "left": 75, "top": 110, "width": 70, "height": 20},
        {"text": "U8", "left": 150, "top": 110, "width": 25, "height": 20},
        {"text": "Rancheras", "left": 205, "top": 110, "width": 80, "height": 20},
        {"text": "Flag", "left": 290, "top": 110, "width": 35, "height": 20},
        {"text": "U8", "left": 330, "top": 110, "width": 25, "height": 20},
    ]

    result = parse_game_schedule_ocr_words(1000, 500, words, TEAMS)

    assert result["matched"] == 1
    assert result["proposals"][0]["week"] == 1
    assert result["proposals"][0]["field_number"] == 1


def test_browser_ocr_infers_field_count_from_team_matches_without_headers():
    words = [
        {"text": "Semana", "left": 700, "top": 5, "width": 80, "height": 20},
        {"text": "1", "left": 790, "top": 5, "width": 10, "height": 20},
        {"text": "12:00", "left": 4, "top": 110, "width": 35, "height": 20},
        {"text": "Nomadas", "left": 75, "top": 110, "width": 70, "height": 20},
        {"text": "U8", "left": 150, "top": 110, "width": 25, "height": 20},
        {"text": "Rancheras", "left": 205, "top": 110, "width": 80, "height": 20},
        {"text": "Flag", "left": 290, "top": 110, "width": 35, "height": 20},
        {"text": "U8", "left": 330, "top": 110, "width": 25, "height": 20},
    ]

    result = parse_game_schedule_ocr_words(
        1000,
        500,
        words,
        TEAMS,
        recognized_text="Semana 1",
    )

    assert result["matched"] == 1
    assert result["proposals"][0]["field_number"] == 1
