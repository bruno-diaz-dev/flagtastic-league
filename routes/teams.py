from fastapi import APIRouter, HTTPException


from repositories.players import get_players_by_team
from models import TeamCreate
from repositories.teams import (
    create_team,
    get_all_teams,
    get_team_by_id
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

@router.get("/{team_id}")
def get_team_details(team_id: int):
    team = get_team_by_id(team_id)

    if team is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    players = get_players_by_team(team_id)

    return {
        **team,
        "players": [
            {
                "id": player["id"],
                "name": player["name"],
                "age": player["age"],
                "jersey_number": player["jersey_number"]
            }

            for player in players
        ]
    }