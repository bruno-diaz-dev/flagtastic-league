"""Authentication and least-privilege authorization dependencies."""

from fastapi import Cookie, Depends, HTTPException

from repositories.users import user_represents_team
from services.auth import get_authenticated_user
from settings import SESSION_COOKIE_NAME


def require_authenticated_user(
    session_token: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME
    )
):
    """Resolve an active session or reject the request uniformly."""
    user = (
        get_authenticated_user(session_token)
        if session_token is not None
        else None
    )
    if user is None:
        raise HTTPException(status_code=401, detail="No autenticado")
    return user


def require_league_admin(user=Depends(require_authenticated_user)):
    """Allow only league administrators to perform league-wide writes."""
    if user["role"] != "league_admin":
        raise HTTPException(status_code=403, detail="Acceso no autorizado")
    return user


def require_team_creator(user=Depends(require_authenticated_user)):
    """Allow administrators and representatives to create teams."""
    if user["role"] not in {"league_admin", "team_representative"}:
        raise HTTPException(status_code=403, detail="Acceso no autorizado")
    return user


def require_player(user=Depends(require_authenticated_user)):
    """Allow only player accounts linked to a player identity."""
    if user["role"] != "player" or user.get("player_id") is None:
        raise HTTPException(status_code=403, detail="Acceso no autorizado")
    return user


def require_team_manager(
    team_id: int,
    user=Depends(require_authenticated_user)
):
    """Allow admins or a representative assigned to the selected team."""
    if user["role"] == "league_admin":
        return user
    if (
        user["role"] == "team_representative"
        and user_represents_team(user["id"], team_id)
    ):
        return user
    raise HTTPException(status_code=403, detail="Acceso no autorizado")
