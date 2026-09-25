"""User persistence and password hashing helpers."""

import hashlib
import hmac
import secrets

from database import get_connection

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 390000


def _public_user(row):
    """Add a public display name while preserving the account's legal name."""
    user = dict(row)
    user["roles"] = list(user.get("roles") or [user["role"]])
    aka = user.pop("player_aka", None)
    user["aka"] = aka
    user["display_name"] = aka or user["name"]
    if user.get("player_id") is None:
        user.pop("player_id", None)
    return user

def hash_password(password):
    """Hash a password with a unique salt using PBKDF2-SHA256."""
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS
    ).hex()

    return (
        f"{PASSWORD_ALGORITHM}"
        f"${PASSWORD_ITERATIONS}"
        f"${salt}"
        f"${password_hash}"
    )

def verify_password(password, stored_password_hash):
    """Return whether a password matches a stored PBKDF2-SHA256 hash."""
    try:
        algorithm, iterations, salt, expected_hash = stored_password_hash.split("$")

    except ValueError:
        return False

    if algorithm != PASSWORD_ALGORITHM:
        return False

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations)
    ).hex()

    return hmac.compare_digest(password_hash, expected_hash)

def create_user(user):
    """Create a user and return only fields safe for application use."""
    connection = get_connection()

    password_hash = hash_password(user.password)

    try:
        created_user = connection.execute(
            """
            INSERT INTO users (
                email,
                name,
                password_hash,
                role
            )
            VALUES (%s, %s, %s, %s)
            RETURNING
                id,
                email,
                name,
                role,
                status
            """,
            (
                user.email,
                user.name.strip(),
                password_hash,
                user.role
            )
        ).fetchone()

        connection.execute(
            "INSERT INTO user_roles (user_id, role) VALUES (%s, %s)",
            (created_user["id"], user.role)
        )

        connection.commit()

        return _public_user({**dict(created_user), "roles": [user.role]})

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


class PlayerIdentityConflict(Exception):
    """Raised when an existing CURP cannot be claimed by a registration."""


def create_player_account(registration, profile_photo_path):
    """Create a player identity and linked login in one transaction.

    Existing roster players may claim their identity only when name and age
    match. This prevents silently attaching an account to a different person.
    """
    connection = get_connection()
    try:
        player = connection.execute(
            "SELECT id, name, age FROM players WHERE curp = %s FOR UPDATE",
            (registration.curp,)
        ).fetchone()

        if player is not None and (
            player["name"].strip().casefold() != registration.name.strip().casefold()
            or player["age"] != registration.age
        ):
            raise PlayerIdentityConflict()

        if player is None:
            player = connection.execute(
                """
                INSERT INTO players (name, curp, age, aka, profile_photo_path)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, name, age
                """,
                (
                    registration.name.strip(), registration.curp,
                    registration.age, registration.aka, profile_photo_path
                )
            ).fetchone()
        else:
            connection.execute(
                """
                UPDATE players
                SET aka = %s, profile_photo_path = %s
                WHERE id = %s
                """,
                (registration.aka, profile_photo_path, player["id"])
            )

        password_hash = hash_password(registration.password.get_secret_value())
        created_user = connection.execute(
            """
            INSERT INTO users (email, name, password_hash, role, player_id)
            VALUES (%s, %s, %s, 'player', %s)
            RETURNING id, email, name, role, status, player_id
            """,
            (
                registration.email,
                registration.name.strip(),
                password_hash,
                player["id"]
            )
        ).fetchone()
        connection.execute(
            "INSERT INTO user_roles (user_id, role) VALUES (%s, 'player')",
            (created_user["id"],)
        )
        connection.commit()
        return _public_user({
            **dict(created_user),
            "roles": ["player"],
            "player_aka": registration.aka
        })
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def get_user_by_email(email):
    """Return public user data for a normalized email, or None."""
    connection = get_connection()

    row = connection.execute(
        """
        SELECT
            users.id, users.email, users.name, users.role, users.status,
            users.player_id,
            ARRAY(SELECT role FROM user_roles WHERE user_id = users.id ORDER BY role) AS roles,
            players.aka AS player_aka
        FROM users
        LEFT JOIN players ON players.id = users.player_id
        WHERE users.email = %s
        """,
        (email.strip().lower(),)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return _public_user(row)

def get_user_credentials_by_email(email):
    """Return credential data used exclusively during authentication."""
    connection = get_connection()

    row = connection.execute(
        """
        SELECT
            users.id, users.email, users.name, users.password_hash,
            users.role, users.status, users.player_id,
            ARRAY(SELECT role FROM user_roles WHERE user_id = users.id ORDER BY role) AS roles,
            players.aka AS player_aka
        FROM users
        LEFT JOIN players ON players.id = users.player_id
        WHERE users.email = %s
        """,
        (email.strip().lower(),)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return _public_user(row)

def get_user_by_id(user_id):
    """Return public user data for an identifier, or None."""
    connection = get_connection()

    row = connection.execute(
        """
        SELECT
            users.id, users.email, users.name, users.role, users.status,
            users.player_id,
            ARRAY(SELECT role FROM user_roles WHERE user_id = users.id ORDER BY role) AS roles,
            players.aka AS player_aka
        FROM users
        LEFT JOIN players ON players.id = users.player_id
        WHERE users.id = %s
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return _public_user(row)


def user_represents_team(user_id, team_id):
    """Return whether a representative is explicitly assigned to a team."""
    connection = get_connection()
    row = connection.execute(
        """
        SELECT 1
        FROM team_representatives
        WHERE user_id = %s AND team_id = %s
        """,
        (user_id, team_id)
    ).fetchone()
    connection.close()
    return row is not None


def get_all_users():
    """Return user administration fields without credential material."""
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT users.id, users.email, users.name, users.role, users.status,
            users.player_id, players.aka AS player_aka,
            ARRAY(SELECT role FROM user_roles WHERE user_id = users.id ORDER BY role) AS roles
        FROM users
        LEFT JOIN players ON players.id = users.player_id
        ORDER BY COALESCE(NULLIF(players.aka, ''), users.name), users.email
        """
    ).fetchall()
    connection.close()
    return [_public_user(row) for row in rows]


def set_user_roles(user_id, roles):
    """Replace an account's role set while preserving identity constraints."""
    connection = get_connection()
    try:
        user = connection.execute(
            "SELECT player_id FROM users WHERE id = %s FOR UPDATE",
            (user_id,)
        ).fetchone()
        if user is None:
            return None
        if "player" in roles and user["player_id"] is None:
            raise PlayerIdentityConflict()

        connection.execute("DELETE FROM user_roles WHERE user_id = %s", (user_id,))
        for role in sorted(roles):
            connection.execute(
                "INSERT INTO user_roles (user_id, role) VALUES (%s, %s)",
                (user_id, role)
            )

        # Keep the legacy primary role stable for older integrations.
        primary_role = next(
            (role for role in ("league_admin", "team_representative", "player", "referee") if role in roles)
        )
        connection.execute(
            "UPDATE users SET role = %s WHERE id = %s",
            (primary_role, user_id)
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return get_user_by_id(user_id)


def update_user_role(user_id, role):
    """Compatibility helper that replaces the account with one role."""
    return set_user_roles(user_id, {role})
