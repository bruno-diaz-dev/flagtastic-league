"""Safe test configuration and shared authorization overrides."""

import os

import pytest

# Local tests always use a dedicated database, even if the application shell
# currently points DATABASE_URL at development data. GitHub Actions provides
# its own disposable PostgreSQL service through DATABASE_URL.
if not os.getenv("CI"):
    os.environ["DATABASE_URL"] = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://flagtastic:flagtastic@localhost:5432/flagtastic_test"
    )

from dependencies.auth import (
    require_league_admin,
    require_team_creator,
    require_team_manager
)
from main import app


TEST_ADMIN = {
    "id": 0,
    "email": "test-admin@flagtastic.local",
    "name": "Test Admin",
    "role": "league_admin",
    "status": "active"
}


@pytest.fixture(autouse=True)
def authorize_domain_test_writes():
    """Keep domain tests focused while authorization has a dedicated suite."""
    app.dependency_overrides[require_league_admin] = lambda: TEST_ADMIN
    app.dependency_overrides[require_team_creator] = lambda: TEST_ADMIN
    app.dependency_overrides[require_team_manager] = lambda: TEST_ADMIN
    yield
    app.dependency_overrides.clear()
