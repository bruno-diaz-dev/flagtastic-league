"""Authenticated referee directory and self-service profile photo endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from dependencies.auth import require_authenticated_user, require_referee
from repositories.referees import (
    get_referee_profile,
    get_referee_roster,
    update_referee_photo,
)
from services.profile_photos import save_profile_photo


router = APIRouter(prefix="/api/referees", tags=["referees"])


@router.get("")
def list_referees(_user=Depends(require_authenticated_user)):
    """Expose the active officiating roster only to signed-in users."""
    return get_referee_roster()


@router.get("/me")
def my_referee_profile(user=Depends(require_referee)):
    """Return the signed-in referee's effective public profile photo."""
    profile = get_referee_profile(user["id"])
    if profile is None:
        raise HTTPException(status_code=404, detail="Arbitro no encontrado")
    return profile


@router.put("/me/photo", status_code=204)
async def upload_my_referee_photo(
    file: UploadFile = File(...),
    user=Depends(require_referee),
):
    """Let a referee complete or replace their own directory photo."""
    photo = await save_profile_photo(file)
    if not update_referee_photo(user["id"], photo):
        raise HTTPException(status_code=404, detail="Arbitro no encontrado")
