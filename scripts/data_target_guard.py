"""Refuse to run mock-data scripts unless the target is explicitly not Production."""

import os


ALLOWED_TARGETS = {"local", "preview", "test"}


def require_non_production_target(script_name):
    """Stop unless FLAGTASTIC_DATA_TARGET names a non-production database.

    The seed and balance scripts write fake teams, players, scores and
    accounts. DATABASE_URL alone cannot tell Preview from Production, so the
    operator confirms the target explicitly before anything is written.
    """
    target = os.getenv("FLAGTASTIC_DATA_TARGET", "").strip().lower()
    if target not in ALLOWED_TARGETS:
        raise SystemExit(
            f"{script_name} escribe datos de prueba y nunca debe correr contra "
            "Production. Si DATABASE_URL apunta a una base local o de Preview, "
            "define FLAGTASTIC_DATA_TARGET=local o FLAGTASTIC_DATA_TARGET=preview "
            "y vuelve a ejecutarlo."
        )
