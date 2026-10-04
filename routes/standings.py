"""HTTP endpoint for division standings."""

from fastapi import APIRouter, Response

from repositories.standings import get_standings

router = APIRouter(
    prefix="/api/standings",
    tags=["standings"]
)

@router.get("")
def list_standings(
    branch: str,
    category: str,
    response: Response
):
    """Return calculated standings for a branch and category."""
    response.headers["Cache-Control"] = "public, max-age=0, must-revalidate"
    response.headers["Vercel-CDN-Cache-Control"] = "public, max-age=30"
    return get_standings(branch, category)
