"""League-wide user administration restricted to league administrators."""

from fastapi import APIRouter, Depends, HTTPException

from dependencies.auth import require_league_admin
from models import UserRoleUpdate
from repositories.users import (
    PlayerIdentityConflict,
    get_all_users,
    update_user_role
)


router = APIRouter(prefix="/api/admin/users", tags=["administration"])


@router.get("")
def list_users(_admin=Depends(require_league_admin)):
    """List accounts using only fields needed for role administration."""
    return get_all_users()


@router.patch("/{user_id}/role")
def change_user_role(
    user_id: int,
    update: UserRoleUpdate,
    admin=Depends(require_league_admin)
):
    """Grant or revoke roles without allowing accidental self-demotion."""
    if user_id == admin["id"] and update.role != "league_admin":
        raise HTTPException(
            status_code=409,
            detail="No puedes retirar tu propio rol de administrador"
        )
    try:
        user = update_user_role(user_id, update.role)
    except PlayerIdentityConflict as error:
        raise HTTPException(
            status_code=409,
            detail="La cuenta no esta vinculada a un jugador"
        ) from error
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user
