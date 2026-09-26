"""Authenticated player dashboard and self-service roster endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from psycopg.errors import UniqueViolation

from dependencies.auth import require_player, require_team_representative
from models import PlayerProfileUpdate, TeamMembershipCreate
from repositories.dashboard import get_player_dashboard, update_player_aka
from repositories.players import join_team, PlayerAlreadyRegisteredInDivision
from repositories.teams import get_team_by_id
from repositories.representative_dashboard import get_representative_dashboard


router = APIRouter(prefix="/api/me", tags=["dashboard"])


@router.get("/representative-dashboard")
def representative_dashboard(user=Depends(require_team_representative)):
    """Return data only for teams explicitly assigned to this representative."""
    return get_representative_dashboard(user["id"])


@router.patch("/profile")
def update_my_profile(profile: PlayerProfileUpdate, user=Depends(require_player)):
    """Let a player maintain the AKA used in public league views."""
    updated = update_player_aka(user["player_id"], profile.aka)
    if updated is None:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    return updated


@router.get("/dashboard")
def player_dashboard(user=Depends(require_player)):
    """Return only data belonging to the authenticated player."""
    dashboard = get_player_dashboard(user["player_id"])
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    return dashboard


@router.post("/teams/{team_id}", status_code=201)
def register_my_team(
    team_id: int,
    membership: TeamMembershipCreate,
    user=Depends(require_player)
):
    """Let a player join one team per branch and category."""
    team = get_team_by_id(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    try:
        return join_team(user["player_id"], team, membership.jersey_number)
    except PlayerAlreadyRegisteredInDivision as error:
        raise HTTPException(
            status_code=409,
            detail="Ya estas registrado en esta rama y categoria"
        ) from error
    except UniqueViolation as error:
        if error.diag.constraint_name == "team_players_team_id_jersey_number_key":
            detail = "Ese numero ya esta registrado en este equipo"
        else:
            detail = "Ya estas registrado en este equipo"
        raise HTTPException(status_code=409, detail=detail) from error
