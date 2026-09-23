"""Authentication services for credentials and persistent sessions."""

from repositories.users import (
    get_user_credentials_by_email,
    verify_password,
    get_user_by_id
)

from repositories.sessions import get_active_session

def authenticate_user(email, password):
    """Authenticate active credentials without exposing the password hash."""
    credentials = get_user_credentials_by_email(email)

    if credentials is None:
        return None
    
    if credentials["status"] != "active":
        return None

    if not verify_password(
        password,
        credentials["password_hash"]
    ):
        return None

    return {
        "id": credentials["id"],
        "email": credentials["email"],
        "name": credentials["name"],
        "role": credentials["role"],
        "status": credentials["status"]
    }

def get_authenticated_user(token):
    """Resolve an active public user from a valid session token."""
    session = get_active_session(token)

    if session is None:
        return None
    
    user = get_user_by_id(
        session["user_id"]
    )

    if user is None:
        return None

    if user["status"] != "active":
        return None

    return user
