"""Authentication and least-privilege authorization dependencies."""

from fastapi import Cookie, Depends, HTTPException

from repositories.users import user_represents_team
from services.auth import get_authenticated_user
from settings import SESSION_COOKIE_NAME


def user_has_role(user, role):
    """Support cumulative roles while legacy sessions still expose `role`."""
    return role in user.get("roles", [user.get("role")])


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
    if user.get("must_change_password"):
        raise HTTPException(
            status_code=403,
            detail="Debes cambiar tu contraseña antes de continuar"
        )
    return user


def optional_authenticated_user(
    session_token: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME
    )
):
    """Resolve a session when present without blocking public endpoints."""
    if session_token is None:
        return None
    return get_authenticated_user(session_token)


def require_league_admin(user=Depends(require_authenticated_user)):
    """Allow only league administrators to perform league-wide writes."""
    if not user_has_role(user, "league_admin"):
        raise HTTPException(status_code=403, detail="Acceso no autorizado")
    return user


def require_team_creator(user=Depends(require_authenticated_user)):
    """Allow administrators and representatives to create teams."""
    allowed_roles = {"league_admin", "team_representative"}
    if not any(user_has_role(user, role) for role in allowed_roles):
        raise HTTPException(status_code=403, detail="Acceso no autorizado")
    return user


def require_player(user=Depends(require_authenticated_user)):
    """Allow only player accounts linked to a player identity."""
    if not user_has_role(user, "player") or user.get("player_id") is None:
        raise HTTPException(status_code=403, detail="Acceso no autorizado")
    return user


def require_team_representative(user=Depends(require_authenticated_user)):
    """Allow accounts explicitly carrying the representative role."""
    if not user_has_role(user, "team_representative"):
        raise HTTPException(status_code=403, detail="Acceso no autorizado")
    return user


def require_team_manager(
    team_id: int,
    user=Depends(require_authenticated_user)
):
    """Allow admins or a representative assigned to the selected team."""
    if user_has_role(user, "league_admin"):
        return user
    if (
        user_has_role(user, "team_representative")
        and user_represents_team(user["id"], team_id)
    ):
        return user
    raise HTTPException(status_code=403, detail="Acceso no autorizado")


def require_referee(user=Depends(require_authenticated_user)):
    """Allow only users explicitly granted the referee role."""
    if not user_has_role(user, "referee"):
        raise HTTPException(status_code=403, detail="Acceso no autorizado")
    return user
