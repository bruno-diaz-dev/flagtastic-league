"""HTTP endpoint for division standings."""

from fastapi import APIRouter

from repositories.standings import get_standings
from services.divisions import canonicalize_division

router = APIRouter(
    prefix="/api/standings",
    tags=["standings"]
)

@router.get("")
def list_standings(
    branch: str,
    category: str
):
    """Return calculated standings for a branch and category."""
    branch, category = canonicalize_division(branch, category)
    return get_standings(branch, category)
