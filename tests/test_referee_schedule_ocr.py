"""Unit tests for referee-role image extraction before database writes."""

from io import BytesIO

from PIL import Image

from services.referee_schedule_ocr import _best_referee, _grid_row_time, parse_referee_schedule_image


def test_matching_never_selects_the_first_of_two_accent_collisions():
    people=[{'id':11,'name':'Zoe García','display_name':'Zoe','aka':'Zoe'},
            {'id':12,'name':'Zoé Pérez','display_name':'Zoé','aka':'Zoé'}]
    for candidates in [people,list(reversed(people))]:
        for printed in ['Zoe','Zoé','ZOE','Zoes']:
            assert _best_referee(printed,candidates) is None
        assert _best_referee('ZOE',candidates,preserve_accents=True)[0]['id']==11
        assert _best_referee('Zoe\u0301',candidates,preserve_accents=True)[0]['id']==12
        assert _best_referee('Zoe García',candidates)[0]['id']==11
        assert _best_referee('Zoé Pérez',candidates)[0]['id']==12


def test_ocr_fallback_leaves_colliding_zoe_names_unassigned(monkeypatch):
    image=Image.new('RGB',(40,40),'white');content=BytesIO();image.save(content,format='PNG')
    monkeypatch.setattr('services.referee_schedule_ocr.pytesseract.image_to_string',
                        lambda image,config:'Campo 1 Tigres vs Ravens Zoe Alan')
    people=[{'id':11,'name':'Zoe García','display_name':'Zoe'},
            {'id':12,'name':'Zoé Pérez','display_name':'Zoé'},
            {'id':13,'name':'Alan','display_name':'Alan'}]
    games=[{'id':44,'week':4,'home_team':{'name':'Tigres'},'away_team':{'name':'Ravens'}}]
    result=parse_referee_schedule_image(content.getvalue(),games,people)
    assert result['proposals'][0]['officials']==[]
    assert 'ambiguos' in result['warnings'][0]


def test_grid_time_uses_printed_hour_instead_of_row_position():
    words = [
        {"text": "11:00", "x": 20, "y": 130},
        {"text": "12:00", "x": 20, "y": 230},
        {"text": "Cam", "x": 200, "y": 150},
    ]

    assert _grid_row_time(words, 100, 200, 50) == "11:00"
    assert _grid_row_time(words, 200, 300, 50) == "12:00"
    assert _grid_row_time(words, 300, 400, 50) is None


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


def test_schedule_ocr_matches_referee_by_aka(monkeypatch):
    image = Image.new("RGB", (40, 40), "white")
    content = BytesIO()
    image.save(content, format="PNG")
    monkeypatch.setattr(
        "services.referee_schedule_ocr.pytesseract.image_to_string",
        lambda image, config: "Campo 2 Tigres vs Ravens Central"
    )
    games = [{
        "id": 45,
        "week": 4,
        "home_team": {"name": "Tigres"},
        "away_team": {"name": "Ravens"}
    }]
    referees = [{
        "id": 10,
        "name": "Nombre Legal",
        "aka": "Central",
        "display_name": "Central"
    }]

    parsed = parse_referee_schedule_image(content.getvalue(), games, referees)

    official = parsed["proposals"][0]["officials"][0]
    assert official["user_id"] == 10
    assert official["name"] == "Central"
