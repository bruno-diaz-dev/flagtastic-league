"""HTTP endpoints for creating and revoking authenticated sessions."""

from fastapi import (
    APIRouter, BackgroundTasks, Cookie, File, Form, HTTPException, Response,
    UploadFile,
)

from models import (
    LoginRequest, PasswordChange, PasswordResetConfirmation,
    PasswordResetRequest, PlayerAccountCreate,
)
from psycopg.errors import UniqueViolation
from repositories.users import (
    PlayerIdentityConflict,
    change_user_password,
    create_player_account
)
from repositories.sessions import (
    create_session,
    revoke_session
)
from repositories.password_resets import (
    consume_password_reset,
    create_password_reset,
)
from services.auth import (
    authenticate_user,
    get_authenticated_user
)
from services.profile_photos import remove_profile_photo, save_profile_photo
from services.email import send_password_reset_email
from settings import (
    PUBLIC_BASE_URL,
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
    age: int | None = Form(default=None),
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
    profile_photo = await save_profile_photo(photo)
    try:
        return create_player_account(registration, profile_photo)
    except PlayerIdentityConflict as error:
        remove_profile_photo(profile_photo)
        raise HTTPException(
            status_code=409,
            detail="Los datos no coinciden con el jugador registrado"
        ) from error
    except UniqueViolation as error:
        remove_profile_photo(profile_photo)
        constraint = error.diag.constraint_name
        if constraint == "users_email_key":
            detail = "El correo ya esta registrado"
        elif constraint == "users_player_id_key":
            detail = "El jugador ya tiene una cuenta"
        else:
            raise
        raise HTTPException(status_code=409, detail=detail) from error
    except Exception:
        remove_profile_photo(profile_photo)
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


@router.post("/change-password", status_code=204)
def change_password(
    update: PasswordChange,
    session_token: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME
    )
):
    """Change the current password, including mandatory first-login changes."""
    if session_token is None:
        raise HTTPException(status_code=401, detail="No autenticado")
    user = get_authenticated_user(session_token)
    if user is None:
        raise HTTPException(status_code=401, detail="No autenticado")
    changed = change_user_password(
        user["id"],
        update.current_password.get_secret_value(),
        update.new_password.get_secret_value()
    )
    if not changed:
        raise HTTPException(status_code=400, detail="La contraseña actual no coincide")


@router.post("/forgot-password", status_code=202)
def forgot_password(
    reset_request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
):
    """Send a reset link while returning the same response for every email."""
    reset = create_password_reset(reset_request.email)
    if reset is not None:
        reset_url = f"{PUBLIC_BASE_URL}/reset-password?token={reset['token']}"
        background_tasks.add_task(
            send_password_reset_email,
            reset["email"],
            reset_url,
        )
    return {
        "message": (
            "Si existe una cuenta con ese correo, recibirás un enlace para "
            "restablecer tu contraseña."
        )
    }


@router.post("/reset-password", status_code=204)
def reset_password(confirmation: PasswordResetConfirmation):
    """Replace a password using a valid single-use token."""
    changed = consume_password_reset(
        confirmation.token,
        confirmation.new_password.get_secret_value(),
    )
    if not changed:
        raise HTTPException(
            status_code=400,
            detail="El enlace es inválido o ya venció",
        )

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
