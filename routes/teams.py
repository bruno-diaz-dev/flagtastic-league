"""HTTP endpoints for team registration and roster-aware team details."""

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from psycopg.errors import UniqueViolation

from repositories.players import get_players_by_team
from models import TeamCreate, TeamNameUpdate, TeamStaffUpdate, TeamStatusUpdate
from repositories.teams import (
    assign_team_representative,
    create_team,
    delete_team,
    get_all_teams,
    get_team_representative_assignments,
    get_team_by_id,
    get_team_logo,
    update_team_logo,
    update_team_name,
    update_team_staff,
    update_team_status
)
from dependencies.auth import (
    require_league_admin,
    require_team_creator,
    require_team_manager
)
from services.profile_photos import save_team_logo

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
        # The creator becomes an explicit manager regardless of their other roles.
        return create_team(team, user["id"])

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Team already registered in this branch and category"
        )

@router.get("")
def list_teams():
    """Return every registered team."""
    return get_all_teams()


@router.get("/representative-assignments")
def list_team_representative_assignments(
    _user=Depends(require_league_admin)
):
    """Let administrators verify the representatives assigned to each team."""
    return get_team_representative_assignments()


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


@router.put("/{team_id}/logo", status_code=204)
async def upload_team_logo(
    team_id: int,
    file: UploadFile = File(...),
    _user=Depends(require_team_manager)
):
    """Allow a team manager to attach or replace the team's public logo."""
    if get_team_by_id(team_id) is None:
        raise HTTPException(status_code=404, detail="Team not found")
    logo = await save_team_logo(file)
    update_team_logo(team_id, logo["content"], logo["media_type"])


@router.patch("/{team_id}/staff")
def edit_team_staff(
    team_id: int,
    staff: TeamStaffUpdate,
    _user=Depends(require_team_manager)
):
    """Let an assigned representative maintain public roster staff."""
    updated = update_team_staff(team_id, staff)
    if updated is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return updated


@router.patch("/{team_id}/status")
def edit_team_status(
    team_id: int,
    payload: TeamStatusUpdate,
    _user=Depends(require_league_admin)
):
    """Allow league administrators to approve or deactivate a team."""
    updated = update_team_status(team_id, payload.status)
    if updated is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return updated


@router.patch("/{team_id}/name")
def edit_team_name(
    team_id: int,
    payload: TeamNameUpdate,
    _user=Depends(require_league_admin)
):
    """Allow only league administrators to correct a team name."""
    try:
        updated = update_team_name(team_id, payload.name)
    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Team already registered in this branch and category"
        )
    if updated is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return updated


@router.put("/{team_id}/representatives/{user_id}", status_code=204)
def link_team_representative(
    team_id: int,
    user_id: int,
    _user=Depends(require_league_admin)
):
    """Repair or extend ownership for teams created before auto-linking."""
    if not assign_team_representative(team_id, user_id):
        raise HTTPException(
            status_code=404,
            detail="Team or representative not found"
        )


@router.get("/{team_id}/logo")
def read_team_logo(team_id: int):
    """Serve a persisted team logo with its validated media type."""
    logo = get_team_logo(team_id)
    if logo is None:
        raise HTTPException(status_code=404, detail="Logo not found")
    return Response(
        content=logo["logo_data"],
        media_type=logo["logo_type"],
        headers={"Cache-Control": "public, max-age=3600"}
    )


@router.delete("/{team_id}", status_code=204)
def remove_team(team_id: int, _user=Depends(require_league_admin)):
    """Allow league administrators to remove an erroneous team record."""
    if not delete_team(team_id):
        raise HTTPException(status_code=404, detail="Team not found")
