from fastapi import APIRouter


from models import TeamCreate
from repositories.teams import (
    create_team,
    get_all_teams
)

router = APIRouter(
    prefix="/api/teams",
    tags=["teams"]
)

@router.post("", status_code=201)
def register_team(team: TeamCreate):
    return create_team(team)

@router.get("")
def list_teams():
    return get_all_teams()