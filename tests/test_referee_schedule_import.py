"""Structured referee schedule parsing tests."""

from io import BytesIO

from openpyxl import Workbook

from services.referee_schedule_import import parse_referee_schedule_file


GAMES = [{
    "id": 81,
    "week": 5,
    "field_number": 1,
    "start_time": "12:00",
    "home_team": {
        "id": 1, "name": "Nomadas U8", "branch": "mixto", "category": "u8"
    },
    "away_team": {
        "id": 2, "name": "Lobos U8", "branch": "mixto", "category": "u8"
    },
}]
REFEREES = [
    {"id": 11, "name": "Cameron Referee", "display_name": "Cam"},
    {"id": 12, "name": "Alan Judge", "display_name": "Alan"},
    {"id": 13, "name": "Miguel Field", "display_name": "Miguel"},
    {"id": 14, "name": "Allison Stats", "display_name": "Allison"},
]


def test_xlsx_grid_reads_game_row_and_ordered_official_row():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Semana 5"
    sheet.append(["Semana 5"])
    sheet.append(["Hora", "Campo 1", None])
    sheet.append(["12:00", "Nómadas U8", "Lobos U8"])
    sheet.append([None, "Cam / Alan / Miguel / Allison", None])
    content = BytesIO()
    workbook.save(content)

    result = parse_referee_schedule_file(
        "rol-arbitros.xlsx", content.getvalue(), GAMES, REFEREES
    )

    assert result["matched"] == 1
    assert result["unmatched"] == 0
    assert result["warnings"] == []
    assert result["proposals"][0]["game_id"] == 81
    assert result["proposals"][0]["scheduled_time"] == "12:00"
    assert result["proposals"][0]["officials"] == [
        {"user_id": 11, "name": "Cam", "position": "referee"},
        {"user_id": 12, "name": "Alan", "position": "down_judge"},
        {"user_id": 13, "name": "Miguel", "position": "field_judge"},
        {"user_id": 14, "name": "Allison", "position": "statistician"},
    ]


def test_csv_table_accepts_explicit_role_columns_and_reports_unknown_names():
    content = (
        "jornada,campo,hora,local,visitante,referee,down judge,field judge,estadistico\n"
        "5,Campo 1,12:00,Nómadas U8,Lobos U8,Cam,Alan,Persona nueva,Allison\n"
    ).encode("utf-8")

    result = parse_referee_schedule_file(
        "rol-arbitros.csv", content, GAMES, REFEREES
    )

    proposal = result["proposals"][0]
    assert proposal["field_number"] == 1
    assert [official["position"] for official in proposal["officials"]] == [
        "referee", "down_judge", "statistician"
    ]
    assert result["matched"] == 1
    assert "Persona nueva" in result["warnings"][0]


def test_structured_schedule_does_not_guess_an_unregistered_game():
    content = (
        "jornada,campo,hora,local,visitante,referee,down judge\n"
        "5,1,12:00,Equipo inexistente,Lobos U8,Cam,Alan\n"
    ).encode("utf-8")

    result = parse_referee_schedule_file("rol.csv", content, GAMES, REFEREES)

    assert result["proposals"] == []
    assert result["unmatched"] == 1
    assert "no se encontro un partido seguro" in result["warnings"][0]
