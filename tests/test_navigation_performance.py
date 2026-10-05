import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.mark.parametrize("path", ["/teams", "/games", "/standings", "/statistics"])
def test_public_navigation_shell_can_be_cached_at_edge(path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["vercel-cdn-cache-control"] == "public, max-age=300"
    assert response.headers["cache-control"] == "public, max-age=0, must-revalidate"
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("path", ["/dashboard", "/referee/games", "/api/auth/me"])
def test_private_pages_and_identity_do_not_use_public_shell_cache(path):
    response = client.get(path)
    assert "vercel-cdn-cache-control" not in response.headers
