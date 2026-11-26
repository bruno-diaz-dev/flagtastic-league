"""Administrator-only finals attendance eligibility report."""

from fastapi import APIRouter, Depends, Response

from dependencies.auth import require_league_admin
from repositories.finals_eligibility import get_players_below_finals_attendance


router = APIRouter(prefix="/api/admin/finals-eligibility", tags=["administration"])


@router.get("")
def list_ineligible_players(response: Response, _admin=Depends(require_league_admin)):
    """List current roster members below the regular-game attendance threshold."""
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vercel-CDN-Cache-Control"] = "no-store"
    return get_players_below_finals_attendance()

