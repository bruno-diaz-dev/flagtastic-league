"""HTTP endpoints for team registration and roster-aware team details."""

from fastapi import APIRouter, HTTPException
from psycopg.errors import UniqueViolation

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
    """Register a team or report a duplicate division entry."""
    try:
        return create_team(team)

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Team already registered in this branch and category"
        )

@router.get("")
def list_teams():
    """Return every registered team."""
    return get_all_teams()

@router.get("/{team_id}")
def get_team_details(team_id: int):
    """Return a team and its public roster, or a 404 response."""
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
