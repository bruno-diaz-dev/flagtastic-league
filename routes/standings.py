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
    return get_standings(branch, category)