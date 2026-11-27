"""PostgreSQL connection helpers shared by repositories and migrations."""

import os

import psycopg
from psycopg.rows import dict_row

# Without a timeout an unreachable database holds a request until the Vercel
# function itself times out; failing fast returns an error the UI can show.
DEFAULT_CONNECT_TIMEOUT_SECONDS = 10


def get_connection():
    """Return a PostgreSQL connection whose rows behave like dictionaries."""
    database_url = os.getenv(
        "DATABASE_URL"
    )

    if database_url is None:
        raise RuntimeError("DATABASE_URL is not configured")

    return psycopg.connect(
        database_url,
        row_factory=dict_row,
        connect_timeout=int(os.getenv(
            "DATABASE_CONNECT_TIMEOUT", DEFAULT_CONNECT_TIMEOUT_SECONDS
        ))
    )
