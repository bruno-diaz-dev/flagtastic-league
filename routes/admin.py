"""League-wide user administration restricted to league administrators."""

from fastapi import APIRouter, Depends, HTTPException
from psycopg.errors import UniqueViolation

from dependencies.auth import require_league_admin
from models import (
    RefereeProfileUpdate,
    StaffAccountCreate,
    UserRoleUpdate,
    UserRolesUpdate,
)
from repositories.referees import update_referee_aka
from repositories.users import (
    PlayerIdentityConflict,
    create_staff_account,
    delete_user_account,
    get_all_users,
    get_user_by_id,
    reset_user_password_by_admin,
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


@router.post("/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    admin=Depends(require_league_admin),
):
    """Issue a temporary password and require the user to replace it."""
    if user_id == admin["id"]:
        raise HTTPException(
            status_code=409,
            detail="Usa Cambiar contraseña para actualizar tu propia cuenta",
        )

    result = reset_user_password_by_admin(user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return result


@router.patch("/{user_id}/referee-aka")
def change_referee_aka(
    user_id: int,
    update: RefereeProfileUpdate,
    _admin=Depends(require_league_admin),
):
    """Let a league administrator maintain an official's public AKA."""
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if "referee" not in user["roles"]:
        raise HTTPException(
            status_code=409,
            detail="El usuario no tiene rol de arbitro",
        )
    if not update_referee_aka(user_id, update.aka):
        raise HTTPException(
            status_code=409,
            detail="El usuario ya no tiene rol de arbitro",
        )
    return get_user_by_id(user_id)


@router.delete("/{user_id}", status_code=204)
def remove_user_account(
    user_id: int,
    admin=Depends(require_league_admin)
):
    """Remove an account without deleting its historical player identity."""
    if user_id == admin["id"]:
        raise HTTPException(
            status_code=409,
            detail="No puedes eliminar tu propia cuenta"
        )
    if not delete_user_account(user_id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
