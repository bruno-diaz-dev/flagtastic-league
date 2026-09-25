"""HTTP endpoints for creating and revoking authenticated sessions."""

from fastapi import APIRouter, Cookie, File, Form, HTTPException, Response, UploadFile

from models import LoginRequest, PlayerAccountCreate
from psycopg.errors import UniqueViolation
from repositories.users import create_player_account, PlayerIdentityConflict
from repositories.sessions import (
    create_session,
    revoke_session
)
from services.auth import (
    authenticate_user,
    get_authenticated_user
)
from services.profile_photos import remove_profile_photo, save_profile_photo
from settings import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    session_cookie_is_secure
)

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"]
)


@router.post("/register/player", status_code=201)
async def register_player_account(
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    curp: str = Form(...),
    age: int = Form(...),
    aka: str | None = Form(default=None),
    photo: UploadFile = File(...)
):
    """Create a player login without exposing credentials or CURP."""
    registration = PlayerAccountCreate(
        email=email,
        password=password,
        name=name,
        curp=curp,
        age=age,
        aka=aka
    )
    photo_filename = await save_profile_photo(photo)
    try:
        return create_player_account(registration, photo_filename)
    except PlayerIdentityConflict as error:
        remove_profile_photo(photo_filename)
        raise HTTPException(
            status_code=409,
            detail="Los datos no coinciden con el jugador registrado"
        ) from error
    except UniqueViolation as error:
        remove_profile_photo(photo_filename)
        constraint = error.diag.constraint_name
        if constraint == "users_email_key":
            detail = "El correo ya esta registrado"
        elif constraint == "users_player_id_key":
            detail = "El jugador ya tiene una cuenta"
        else:
            raise
        raise HTTPException(status_code=409, detail=detail) from error
    except Exception:
        remove_profile_photo(photo_filename)
        raise

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
