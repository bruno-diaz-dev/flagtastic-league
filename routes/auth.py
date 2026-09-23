"""HTTP endpoints for creating and revoking authenticated sessions."""

import os

from fastapi import APIRouter, Cookie, HTTPException, Response

from models import LoginRequest
from repositories.sessions import (
    create_session,
    revoke_session
)
from services.auth import (
    authenticate_user,
    get_authenticated_user
)

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"]
)

SESSION_COOKIE_NAME = "flagtastic_session"
SESSION_MAX_AGE_SECONDS = 12 * 60 * 60

def session_cookie_is_secure():
    """Return whether session cookies must only travel over HTTPS."""

    return (
        os.getenv("SESSION_COOKIE_SECURE", "true").lower()
        == "true"
    )

@router.post("/login")
def login(credentials: LoginRequest, response: Response):
    """Authenticate a user and store the session token in a secure cookie."""

    user = authenticate_user(
        credentials.email,
        credentials.password.get_secret_value()
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Correo o contraseña incorrectos"
        )

    session = create_session(user["id"])

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session["token"],
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=session_cookie_is_secure(),
        samesite="lax",
        path="/"
    )

    return user

@router.get("/me")
def get_current_user(
    session_token: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME
    )
):
    """Return the user associated with the active session cookie."""
    if session_token is None:
        raise HTTPException(
            status_code=401,
            detail="No autenticado"
        )

    user = get_authenticated_user(session_token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="No autenticado"
        )
    
    return user

@router.post("/logout", status_code=204)
def logout(
    response: Response,
    session_token: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME
    )
):
    """Revoke the current session and remove its browser cookie."""
    if session_token is not None:
        revoke_session(session_token)

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=session_cookie_is_secure(),
        httponly=True,
        samesite="lax"
    )