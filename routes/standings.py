"""HTTP endpoint for division standings."""

from fastapi import APIRouter

from repositories.standings import get_standings

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
    return get_standings(branch, category)
