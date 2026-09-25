"""Integration tests for complete-week Excel imports and leaderboards."""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from database import get_connection
from main import app


client = TestClient(app)
HEADERS = [
    "rama", "categoria", "equipo", "numero", "puntos", "recepciones",
    "intercepciones", "capturas", "tacleadas", "pases_completos",
    "pases_lanzados"
]


@pytest.fixture(autouse=True)
def clean_database():
    connection = get_connection()
    connection.execute("DELETE FROM player_week_stats")
    connection.execute("DELETE FROM games")
    connection.execute("DELETE FROM team_players")
    connection.execute("DELETE FROM players")
    connection.execute("DELETE FROM teams")
    connection.commit()
    connection.close()


def create_team(name, branch="varonil", category="libre"):
    return client.post(
        "/api/teams",
        json={"name": name, "branch": branch, "category": category}
    ).json()["id"]


def create_player(team_id, name, curp, number):
    return client.post(
        f"/api/teams/{team_id}/players",
        json={"name": name, "curp": curp, "age": 25, "jersey_number": number}
    ).json()["id"]


def create_workbook(rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(HEADERS)
    for row in rows:
        sheet.append(row)
    content = BytesIO()
    workbook.save(content)
    workbook.close()
    return content.getvalue()


def create_official_workbook():
    """Build the horizontal event layout used by the league's real file."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Estadísticas"
    week_one = workbook.create_sheet("Wk 1")
    week_one.append(["Equipo", "Categoría", "Estadística", 1, 2, 3, 4])
    labels = [
        "Intentos Pase", "Completos Pase", "Para % pases", "Puntos Pase",
        "6 Puntos", "2 Puntos", "1 Puntos", "Intercepciones Pase", "TD",
        "Conv 1", "Conv 2", "Sacks", "Tacleo", "Intercepciones Def",
        "Asistencia"
    ]
    tigres_events = {
        "Intentos Pase": [83], "Completos Pase": [10, 10],
        "Para % pases": [83, 83], "6 Puntos": [83], "TD": [10],
        "Sacks": [22, 22], "Tacleo": [22, 10],
        "Intercepciones Def": [22]
    }
    for label in labels:
        week_one.append(
            ["Tigres", "Var Libre", label, *tigres_events.get(label, [])]
        )
    for label in labels:
        week_one.append(["Ravens", "Var Libre", label])
    content = BytesIO()
    workbook.save(content)
    workbook.close()
    return content.getvalue()


def upload_week(week, rows, filename="estadisticas.xlsx"):
    return client.post(
        f"/api/weeks/{week}/player-stats/import",
        files={"file": (filename, create_workbook(rows))}
    )


def create_rosters():
    tigres = create_team("Tigres")
    ravens = create_team("Ravens")
    panteras = create_team("Panteras", "femenil", "u18")
    bruno = create_player(tigres, "Bruno Diaz", "DIBB961215HASXXX00", 83)
    jose = create_player(ravens, "Jose Perez", "PERJ990201HASXX002", 12)
    ana = create_player(panteras, "Ana Ruiz", "RUIA010101MASXX003", 7)
    return bruno, jose, ana


def test_imports_a_complete_week_and_resolves_names_from_rosters():
    bruno_id, _, _ = create_rosters()
    response = upload_week(2, [
        ["varonil", "libre", "Tigres", 83, 12, 4, 1, 0, 3, 18, 24],
        ["varonil", "libre", "Ravens", 12, 6, 2, 2, 1, 5, 11, 20],
        ["femenil", "u18", "Panteras", 7, 18, 5, 0, 0, 2, 0, 0]
    ])
    assert response.status_code == 200
    assert response.json()["imported"] == 3
    assert {row["player_name"] for row in response.json()["rows"]} == {
        "Bruno Diaz", "Jose Perez", "Ana Ruiz"
    }

    week = client.get("/api/weeks/2/player-stats")
    assert week.status_code == 200
    assert week.json()[0]["week"] == 2

    totals = client.get(f"/api/players/{bruno_id}/stats").json()
    assert totals["weeks"] == 1
    assert totals["points"] == 12
    assert totals["completion_percentage"] == 75.0


def test_imports_the_official_horizontal_workbook_format():
    tigres = create_team("Tigres")
    quarterback = create_player(tigres, "Quarterback", "QBXX010101HASXX001", 83)
    create_player(tigres, "Receiver", "RECX010101HASXX002", 10)
    create_player(tigres, "Defender", "DEFN010101HASXX003", 22)
    ravens = create_team("Ravens")

    response = client.post(
        "/api/statistics/import",
        files={"file": ("Stats ALL.xlsx", create_official_workbook())}
    )
    assert response.status_code == 200
    assert response.json()["weeks"] == [1]
    assert response.json()["imported"] == 3
    assert response.json()["games"] == 1

    totals = client.get(f"/api/players/{quarterback}/stats").json()
    assert totals["passes_attempted"] == 3
    assert totals["passes_completed"] == 2
    leaders = client.get(
        "/api/statistics/leaderboards?branch=varonil&category=libre"
    ).json()
    assert leaders["receptions"][0]["player_name"] == "Receiver"
    assert leaders["points"][0]["value"] == 6
    assert leaders["sacks"][0]["value"] == 2
    games = client.get("/api/games").json()
    assert games[0]["home_team"]["id"] == tigres
    assert games[0]["away_team"]["id"] == ravens
    assert games[0]["home_score"] == 6
    assert games[0]["away_score"] == 0


def test_team_identity_includes_branch_and_category():
    first = create_team("Tigres", "varonil", "libre")
    second = create_team("Tigres", "varonil", "u18")
    create_player(first, "Adulto", "AAAA010101HASXX001", 10)
    create_player(second, "Juvenil", "BBBB010101HASXX002", 10)

    response = upload_week(1, [
        ["varonil", "libre", "Tigres", 10, 6, 1, 0, 0, 0, 1, 2],
        ["varonil", "u18", "Tigres", 10, 12, 2, 0, 0, 0, 2, 3]
    ])
    assert response.status_code == 200
    assert [row["player_name"] for row in response.json()["rows"]] == [
        "Adulto", "Juvenil"
    ]


def test_invalid_roster_row_does_not_replace_the_week_snapshot():
    create_rosters()
    assert upload_week(1, [
        ["varonil", "libre", "Tigres", 83, 12, 3, 0, 0, 1, 5, 10]
    ]).status_code == 200
    invalid = upload_week(1, [
        ["varonil", "libre", "Tigres", 999, 9, 9, 9, 9, 9, 5, 10]
    ])
    assert invalid.status_code == 422
    saved = client.get("/api/weeks/1/player-stats").json()
    assert len(saved) == 1
    assert saved[0]["points"] == 12


def test_a_new_upload_replaces_the_complete_week():
    create_rosters()
    upload_week(1, [
        ["varonil", "libre", "Tigres", 83, 6, 1, 0, 0, 0, 1, 2],
        ["varonil", "libre", "Ravens", 12, 6, 1, 0, 0, 0, 1, 2]
    ])
    upload_week(1, [
        ["varonil", "libre", "Tigres", 83, 18, 3, 0, 0, 0, 2, 3]
    ])
    saved = client.get("/api/weeks/1/player-stats").json()
    assert len(saved) == 1
    assert saved[0]["player_name"] == "Bruno Diaz"
    assert saved[0]["points"] == 18


def test_import_rejects_non_excel_file_and_invalid_week():
    assert client.post(
        "/api/weeks/1/player-stats/import",
        files={"file": ("stats.csv", b"not excel", "text/csv")}
    ).status_code == 415
    assert client.post(
        "/api/weeks/0/player-stats/import",
        files={"file": ("stats.xlsx", create_workbook([]))}
    ).status_code == 422


def test_download_template_contains_roster_identity_columns():
    response = client.get("/api/statistics/import-template")
    assert response.status_code == 200
    workbook = load_workbook(BytesIO(response.content), read_only=True)
    headers = [cell.value for cell in next(workbook.active.iter_rows())]
    workbook.close()
    assert headers == HEADERS
    assert "nombre" not in headers


def test_leaderboards_limit_results_and_apply_passing_threshold():
    tigres = create_team("Tigres")
    rows = []
    for index in range(6):
        number = index + 1
        create_player(tigres, f"Player {number}", f"TEST{number:014d}", number)
        rows.append([
            "varonil", "libre", "Tigres", number,
            6 - index, 1, 0, 0, 0, 1, 2
        ])
    assert upload_week(1, rows).status_code == 200
    leaders = client.get(
        "/api/statistics/leaderboards?branch=varonil&category=libre"
    ).json()
    assert len(leaders["points"]) == 5
    assert leaders["passing_qualification"]["minimum_attempts"] == 0

    qualifying = rows[0].copy()
    qualifying[-2:] = [29, 38]
    assert upload_week(4, [qualifying]).status_code == 200
    leaders = client.get(
        "/api/statistics/leaderboards?branch=varonil&category=libre"
    ).json()
    assert leaders["passing_qualification"] == {
        "latest_week": 4, "minimum_attempts": 30
    }
    assert leaders["completion_percentage"][0]["player_name"] == "Player 1"
    assert "player_aka" in leaders["completion_percentage"][0]
    assert "profile_photo_url" in leaders["completion_percentage"][0]
