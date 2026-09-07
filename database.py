import os

import psycopg
from psycopg.rows import dict_row

def get_connection():
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://flagtastic:flagtastic@localhost:5432/flagtastic"
    )

    return psycopg.connect(
        database_url,
        row_factory=dict_row
    )

def create_database():
    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS teams (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                branch TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
            )
            """
        ) 

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                curp TEXT NOT NULL UNIQUE,
                age INTEGER NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS team_players(
                id SERIAL PRIMARY KEY,
                team_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                jersey_number INTEGER NOT NULL,

                FOREIGN KEY (team_id)
                    REFERENCES teams(id)
                    ON DELETE CASCADE,
                
                FOREIGN KEY (player_id)
                    REFERENCES players(id)
                    ON DELETE CASCADE,
                
                UNIQUE (team_id, player_id),
                UNIQUE (team_id, jersey_number)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS games (
                id SERIAL PRIMARY KEY,
                home_team_id INTEGER NOT NULL,
                away_team_id INTEGER NOT NULL,

                FOREIGN KEY (home_team_id)
                    REFERENCES teams(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (away_team_id)
                    REFERENCES teams(id)
                    ON DELETE CASCADE
            )
            """
        )
        connection.commit()


    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close