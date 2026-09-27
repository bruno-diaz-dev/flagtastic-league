"""Authentication services for credentials and persistent sessions."""

from repositories.users import (
    get_user_credentials_by_email,
    verify_password,
    get_user_by_session_hash
)

from repositories.sessions import hash_session_token

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

    user = {
        "id": credentials["id"],
        "email": credentials["email"],
        "name": credentials["name"],
        "aka": credentials.get("aka"),
        "display_name": credentials["display_name"],
        "role": credentials["role"],
        "roles": credentials["roles"],
        "status": credentials["status"]
    }
    if credentials.get("must_change_password"):
        user["must_change_password"] = True
    return user

def get_authenticated_user(token):
    """Resolve an active public user from a valid session token."""
    return get_user_by_session_hash(hash_session_token(token))
