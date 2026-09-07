from psycopg.errors import UniqueViolation
from fastapi import APIRouter, HTTPException

from models import PlayerCreate
from repositories.teams import get_team_by_id
from repositories.players import (
    create_player,
    get_players_by_team,
    PlayerAlreadyRegisteredInDivision
)

router = APIRouter(
    prefix="/api/teams/{team_id}/players",
    tags=["players"]
)

@router.post("", status_code=201)
def register_player(
    team_id: int,
    player: PlayerCreate
):

    team = get_team_by_id(team_id)

    if team is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    try:
        return create_player(team, player)

    except PlayerAlreadyRegisteredInDivision:

        raise HTTPException(
            status_code=409,
            detail="Player already registered in this branch and category"
        )

    except UniqueViolation as error:
        constraint = error.diag.constraint_name

        if (
            constraint
            == "team_players_team_id_jersey_number_key"
        ):
            raise HTTPException(
                status_code=409,
                detail="Jersey number already registered in this team"
            )
            
        if (
            constraint
            == "team_players_team_id_player_id_key"
        ):
            raise HTTPException(
                status_code=409,
                detail="Player already registered in this team"
            )
        raise

@router.get("")
def list_players(team_id: int):
    return get_players_by_team(team_id)