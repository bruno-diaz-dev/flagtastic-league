from repositories.users import (
    get_user_credentials_by_email,
    verify_password
)

def authenticate_user(email, password):
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