"""Tests for reviewed game imports from league schedule files."""

from io import BytesIO

from openpyxl import Workbook

from services.game_schedule_import import parse_game_schedule_file


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
