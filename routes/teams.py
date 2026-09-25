"""HTTP endpoints for team registration and roster-aware team details."""

from fastapi import APIRouter, Depends, HTTPException
from psycopg.errors import UniqueViolation

from repositories.players import get_players_by_team
from models import TeamCreate
from repositories.teams import (
    create_team,
    delete_team,
    get_all_teams,
    get_team_by_id
)
from dependencies.auth import require_league_admin, require_team_creator

router = APIRouter(
    prefix="/api/teams",
    tags=["teams"]
)

@router.post("", status_code=201)
def register_team(
    team: TeamCreate,
    user=Depends(require_team_creator)
):
    """Register a team or report a duplicate division entry."""
    try:
        representative_id = (
            user["id"] if user["role"] == "team_representative" else None
        )
        return create_team(team, representative_id)

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
                "aka": player["aka"],
                "age": player["age"],
                "profile_photo_url": player["profile_photo_url"],
                "jersey_number": player["jersey_number"]
            }

            for player in players
        ]
    }


@router.delete("/{team_id}", status_code=204)
def remove_team(team_id: int, _user=Depends(require_league_admin)):
    """Allow league administrators to remove an erroneous team record."""
    if not delete_team(team_id):
        raise HTTPException(status_code=404, detail="Team not found")
