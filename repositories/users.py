import hashlib
import hmac
import secrets

from database import get_connection

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 390000

def hash_password(password):
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

        connection.commit()

        return dict(created_user)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def get_user_by_email(email):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT
            id,
            email,
            name,
            role,
            status
        FROM users
        WHERE email = %s
        """,
        (email.strip().lower(),)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return dict(row)

def get_user_credentials_by_email(email):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT
            id,
            email,
            name,
            password_hash,
            role,
            status
        FROM users
        WHERE email = %s
        """,
        (email.strip().lower(),)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return dict(row)
