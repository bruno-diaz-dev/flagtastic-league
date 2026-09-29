"""Tests for reviewed game imports from league schedule files."""

from io import BytesIO

from openpyxl import Workbook
from PIL import Image

from services.game_schedule_import import (
    parse_game_schedule_file,
    parse_game_schedule_image,
    parse_game_schedule_ocr_words,
    parse_game_schedule_ocr_cells,
)


TEAMS = [
    {"id": 1, "name": "Nomadas", "branch": "mixto", "category": "u8"},
    {"id": 2, "name": "Rancheras Flag", "branch": "mixto", "category": "u8"},
    {"id": 3, "name": "Ducks", "branch": "femenil", "category": "libre"},
    {"id": 4, "name": "Storms", "branch": "femenil", "category": "libre"},
]


def test_pitbulls_ir_ocr_matches_jr_without_confusing_sr():
    teams = [
        {"id": 1, "name": "Pitbulls Jr", "branch": "mixto", "category": "libre"},
        {"id": 2, "name": "Pitbulls Sr", "branch": "mixto", "category": "libre"},
        {"id": 3, "name": "Storms", "branch": "mixto", "category": "libre"},
    ]
    from datetime import time
    for label, expected in [("Pitbulls Ir Mix Libre", 1), ("Pitbulls Sr Mix Libre", 2)]:
        result = parse_game_schedule_ocr_cells(1, [{
            "field_number": 1, "start_time": time(21),
            "home_team": label, "away_team": "Storms Mix Libre",
        }], teams)
        row = result["proposals"][0]
        assert row["home_team_id"] == expected
        assert row["away_match"] == "Storms"
        assert row["home_match_category"] == "libre"
        assert row["home_match_branch"] == "mixto"


def test_unreadable_image_time_preserves_matched_teams_for_review():
    result = parse_game_schedule_ocr_cells(1, [{
        "field_number": 1,
        "start_time": None,
        "home_team": "Nomadas U8",
        "away_team": "Rancheras Flag U8",
    }], TEAMS)
    proposal = result["proposals"][0]
    assert proposal["start_time"] is None
    assert proposal["home_team_id"] == 1
    assert proposal["away_team_id"] == 2
    assert proposal["ready"] is True


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
        "home_match_branch": "mixto",
        "home_match_category": "u8",
        "away_team_id": 2,
        "away_match": "Rancheras Flag",
        "away_match_branch": "mixto",
        "away_match_category": "u8",
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


def test_browser_ocr_recovers_split_and_misread_times():
    words = [
        {"text": "Semana", "left": 700, "top": 5, "width": 80, "height": 20},
        {"text": "1", "left": 790, "top": 5, "width": 10, "height": 20},
        {"text": "Campo", "left": 120, "top": 40, "width": 60, "height": 20},
        {"text": "1", "left": 185, "top": 40, "width": 10, "height": 20},
        {"text": "11", "left": 2, "top": 110, "width": 12, "height": 20},
        {"text": ".", "left": 15, "top": 110, "width": 4, "height": 20},
        {"text": "00", "left": 20, "top": 110, "width": 12, "height": 20},
        {"text": "Nomadas", "left": 75, "top": 110, "width": 70, "height": 20},
        {"text": "U8", "left": 150, "top": 110, "width": 25, "height": 20},
        {"text": "Rancheras", "left": 205, "top": 110, "width": 80, "height": 20},
        {"text": "Flag", "left": 290, "top": 110, "width": 35, "height": 20},
        {"text": "U8", "left": 330, "top": 110, "width": 25, "height": 20},
    ]

    result = parse_game_schedule_ocr_words(1000, 500, words, TEAMS)

    assert result["matched"] == 1
    assert result["proposals"][0]["start_time"] == "11:00"


def test_browser_ocr_ignores_field_numbers_above_six():
    words = [
        {"text": "Semana", "left": 700, "top": 5, "width": 80, "height": 20},
        {"text": "1", "left": 790, "top": 5, "width": 10, "height": 20},
        {"text": "Campo", "left": 380, "top": 40, "width": 60, "height": 20},
        {"text": "7", "left": 445, "top": 40, "width": 10, "height": 20},
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
        recognized_text="Semana 1 Campo 7",
    )

    assert all(proposal["field_number"] <= 6 for proposal in result["proposals"])


def test_browser_ocr_uses_selected_week_when_header_is_unreadable():
    words = [
        {"text": "Campo", "left": 120, "top": 40, "width": 60, "height": 20},
        {"text": "1", "left": 185, "top": 40, "width": 10, "height": 20},
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
        recognized_text="texto ilegible",
        week_override=4,
    )

    assert result["matched"] == 1
    assert result["proposals"][0]["week"] == 4


def test_browser_ocr_uses_fixed_six_field_layout_without_field_headers():
    words = [
        {"text": "11:00", "left": 4, "top": 110, "width": 35, "height": 20},
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
        recognized_text="texto sin encabezados de campo",
        week_override=1,
    )

    assert result["proposals"]
    assert all(1 <= proposal["field_number"] <= 6 for proposal in result["proposals"])


def test_segmented_ocr_recovers_common_team_misreads():
    from datetime import time

    teams = [
        {"id": 1, "name": "Ducks", "branch": "femenil", "category": "u12"},
        {"id": 2, "name": "BlackMambas", "branch": "femenil", "category": "u12"},
        {"id": 3, "name": "Ducks", "branch": "femenil", "category": "u14"},
        {"id": 4, "name": "BlackMambas", "branch": "femenil", "category": "u14"},
        {"id": 5, "name": "Diablos", "branch": "mixto", "category": "u12"},
        {"id": 6, "name": "Rancheros", "branch": "mixto", "category": "u12"},
    ]

    result = parse_game_schedule_ocr_cells(
        1,
        [
            {
                "field_number": 1,
                "start_time": time(12, 0),
                "home_team": "Ducks L132 Fem",
                "away_team": "BlackMambas W12 Fem",
            },
            {
                "field_number": 2,
                "start_time": time(12, 0),
                "home_team": "Chablos W12",
                "away_team": "Rancheros U12",
            },
        ],
        teams,
    )

    assert result["matched"] == 2
    assert result["unmatched"] == 0
    assert result["proposals"][0]["home_team_id"] == 1
    assert result["proposals"][0]["away_team_id"] == 2
    assert result["proposals"][1]["home_team_id"] == 5
