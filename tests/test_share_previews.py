"""Link previews: Open Graph tags on public pages and the preview images."""

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

import routes.share as share
from main import app
from services.display_names import display_name, division_label


client = TestClient(app)

GAME = {
    "id": 66, "week": 1, "status": "completed", "home_score": 18, "away_score": 6,
    "field_number": 1, "start_time": "11:00:00", "game_date": None, "venue": None,
    "is_friendly": False, "bracket_label": None, "bracket_pending": False,
    "home_team": {"id": 51, "name": "RANCHEROS", "branch": "mixto", "category": "u8", "logo_url": None},
    "away_team": {"id": 143, "name": "rancheras flag", "branch": "femenil", "category": "u8", "logo_url": None},
}


def _png_size(response):
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    return Image.open(BytesIO(response.content)).size


def test_names_read_like_the_site():
    assert display_name("DIABLOS DEL SOL") == "Diablos del Sol"
    assert display_name("Club ECA Aguascalientes") == "Club ECA Aguascalientes"
    assert display_name("rancheros infantil a.c") == "Rancheros Infantil A.C"
    assert display_name("ruiz-esparza") == "Ruiz-Esparza"
    assert division_label("mixto", "u10") == "Infantiles · U10"
    assert division_label("varonil", "libre") == "Varonil · Libre"


def test_game_page_shares_the_final_score(monkeypatch):
    monkeypatch.setattr(share, "get_games", lambda: [GAME])
    monkeypatch.setattr(share, "get_team_logo", lambda team_id: None)

    page = client.get("/games/66").text
    assert '<meta property="og:title" content="Rancheros 18 – 6 Rancheras Flag">' in page
    assert "/og/games/66.png?v=completed-18-6" in page
    assert '<meta name="twitter:card" content="summary_large_image">' in page

    assert _png_size(client.get("/og/games/66.png")) == (1200, 630)


def test_unknown_game_falls_back_to_the_league_preview(monkeypatch):
    monkeypatch.setattr(share, "get_games", lambda: [])

    page = client.get("/games/999").text
    assert '<meta property="og:title" content="FlagTastic Football League">' in page
    assert "/static/assets/icon-512.png" in page
    assert client.get("/og/games/999.png").status_code == 404


def test_a_database_failure_never_breaks_the_page(monkeypatch):
    def unavailable():
        raise RuntimeError("database unavailable")
    monkeypatch.setattr(share, "get_games", unavailable)

    response = client.get("/games/66")
    assert response.status_code == 200
    assert '<meta property="og:title" content="FlagTastic Football League">' in response.text


def test_team_page_shares_record_and_standing(monkeypatch):
    team = {"id": 104, "name": "LOBOS", "branch": "varonil", "category": "libre"}
    standings = [
        {"team_id": 154, "wins": 5, "losses": 1, "point_difference": 64},
        {"team_id": 104, "wins": 4, "losses": 2, "point_difference": 48},
    ]
    monkeypatch.setattr(share, "get_team_by_id", lambda team_id: team if team_id == 104 else None)
    monkeypatch.setattr(share, "get_standings", lambda branch, category: standings)
    monkeypatch.setattr(share, "get_team_logo", lambda team_id: None)

    page = client.get("/teams/104/roster").text
    assert '<meta property="og:title" content="Lobos · Roster">' in page
    assert "Récord 4-2, lugar 2 de 2" in page
    assert _png_size(client.get("/og/teams/104.png")) == (1200, 630)


def test_player_preview_has_season_totals_and_no_photo(monkeypatch):
    profile = {
        "player": {"id": 7, "name": "ANA LÓPEZ", "aka": None, "age": 14, "profile_photo_url": "/media/profiles/7.png"},
        "selected_team_id": 3,
        "teams": [{"team_id": 3, "team_name": "Tigres", "branch": "femenil", "category": "u14", "jersey_number": 9,
                   "statistics": {"points": 24, "receptions": 8, "tackles": 5, "interceptions": 2, "weeks": 3}}],
    }
    monkeypatch.setattr(share, "get_player_dashboard", lambda player_id, team_id=None: profile)

    page = client.get("/players/7").text
    assert '<meta property="og:title" content="Ana López · Temporada">' in page
    assert "24 puntos" in page
    assert "/og/players/7.png?team_id=3&amp;v=" in page
    assert "/media/profiles/7.png" not in page.split("</head>")[0]
    assert _png_size(client.get("/og/players/7.png")) == (1200, 630)


def test_share_buttons_are_on_shareable_pages(monkeypatch):
    monkeypatch.setattr(share, "get_games", lambda: [GAME])
    monkeypatch.setattr(share, "get_team_logo", lambda team_id: None)
    assert "data-share" in client.get("/games/66").text
