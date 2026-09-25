"""League-wide user administration restricted to league administrators."""

from fastapi import APIRouter, Depends, HTTPException
from psycopg.errors import UniqueViolation

from dependencies.auth import require_league_admin
from models import StaffAccountCreate, UserRoleUpdate, UserRolesUpdate
from repositories.users import (
    PlayerIdentityConflict,
    create_staff_account,
    get_all_users,
    set_user_roles,
    update_user_role
)


router = APIRouter(prefix="/api/admin/users", tags=["administration"])


@router.get("")
def list_users(_admin=Depends(require_league_admin)):
    """List accounts using only fields needed for role administration."""
    return get_all_users()


@router.post("", status_code=201)
def create_staff(
    registration: StaffAccountCreate,
    _admin=Depends(require_league_admin)
):
    """Create an administrator-managed account without requiring a CURP."""
    try:
        return create_staff_account(registration)
    except UniqueViolation as error:
        raise HTTPException(
            status_code=409,
            detail="El correo ya esta registrado"
        ) from error


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


@router.put("/{user_id}/roles")
def replace_user_roles(
    user_id: int,
    update: UserRolesUpdate,
    admin=Depends(require_league_admin)
):
    """Replace cumulative roles without allowing self-admin lockout."""
    if user_id == admin["id"] and "league_admin" not in update.roles:
        raise HTTPException(
            status_code=409,
            detail="No puedes retirar tu propio rol de administrador"
        )
    try:
        user = set_user_roles(user_id, update.roles)
    except PlayerIdentityConflict as error:
        raise HTTPException(
            status_code=409,
            detail="La cuenta no esta vinculada a un jugador"
        ) from error
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user
