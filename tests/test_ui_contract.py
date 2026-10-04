"""Shared navigation and form ownership across all server-rendered screens."""

from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from main import app


PAGE_PATHS = [
    "/teams", "/games", "/games/42", "/standings", "/statistics",
    "/teams/42/roster", "/teams/42/manage", "/dashboard",
    "/representative-dashboard", "/players/42", "/referee/games",
    "/referees", "/referees/42", "/admin/users", "/admin/team-duplicates",
    "/login", "/register", "/forgot-password", "/reset-password",
    "/change-password", "/privacy",
]


class PageContract(HTMLParser):
    """Catch duplicate IDs and forms broken by disclosure restructuring."""

    def __init__(self):
        super().__init__()
        self.ids = set()
        self.form = None
        self.forms = {}
        self.stylesheets = []
        self.main = False
        self.skip_link = False

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        identifier = attrs.get("id")
        if identifier:
            assert identifier not in self.ids, f"Duplicate ID: {identifier}"
            self.ids.add(identifier)
        if tag == "form":
            assert self.form is None, "A form was nested inside another form"
            self.form = identifier
            self.forms[identifier] = set()
        if self.form and tag in {"input", "select", "textarea"} and attrs.get("name"):
            self.forms[self.form].add(attrs["name"])
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.stylesheets.append(attrs["href"])
        if tag == "main" and identifier == "main-content":
            self.main = True
        if tag == "a" and attrs.get("href") == "#main-content":
            self.skip_link = True

    def handle_endtag(self, tag):
        if tag == "form":
            assert self.form is not None, "A form closed without opening"
            self.form = None


@pytest.mark.parametrize("path", PAGE_PATHS)
def test_every_screen_uses_shared_ui_and_accessible_shell(path):
    with TestClient(app) as client:
        response = client.get(path)
    assert response.status_code == 200
    page = PageContract()
    page.feed(response.text)
    assert page.form is None
    assert page.main and page.skip_link
    assert any(href.startswith("/static/ui.css?v=") for href in page.stylesheets)
    assert 'league-page' in response.text


@pytest.mark.parametrize("path,expected", [
    ("/teams", {"team-form": {"name", "branch", "category", "logo", "head_coach", "coach", "manager"}}),
    ("/games", {"game-form": {"home_team_id", "away_team_id", "week", "field_number", "start_time"}, "referee-assignment-form": {"game_id", "referee_id", "position"}}),
    ("/teams/42/roster", {"player-form": {"name", "curp", "age", "jersey_number"}, "team-staff-form": {"head_coach", "coach", "manager"}, "roster-import-form": {"file"}}),
    ("/dashboard", {"profile-form": {"aka"}, "join-team-form": {"team_id", "jersey_number"}}),
])
def test_collapsed_actions_preserve_form_fields_and_ownership(path, expected):
    with TestClient(app) as client:
        page = PageContract()
        page.feed(client.get(path).text)
    for form_id, fields in expected.items():
        assert fields.issubset(page.forms[form_id])
