"""HTTP endpoints for player registration and team rosters."""

from psycopg.errors import UniqueViolation
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from models import PlayerCreate
from repositories.teams import get_team_by_id
from repositories.players import (
    create_player,
    import_players,
    get_players_by_team,
    update_roster_player_photo,
    PlayerAlreadyRegisteredInDivision
)
from dependencies.auth import require_team_manager
from services.roster_import import RosterImportError, parse_roster_file
from services.profile_photos import save_profile_photo

router = APIRouter(
    prefix="/api/teams/{team_id}/players",
    tags=["players"]
)
MAX_ROSTER_IMPORT_BYTES = 5 * 1024 * 1024
ROSTER_CSV_TEMPLATE = (
    "nombre,curp,edad,numero\n"
    "Nombre Completo,ABCD000101HASXXX00,25,10\n"
)

@router.post("", status_code=201)
def register_player(
    team_id: int,
    player: PlayerCreate,
    _user=Depends(require_team_manager)
):
    """Register a player while translating roster conflicts to HTTP errors."""

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
            detail="Este jugador ya esta registrado en esta rama y categoria"
        )

    except UniqueViolation as error:
        # Constraint names distinguish a duplicate jersey from a duplicate member.
        constraint = error.diag.constraint_name

        if (
            constraint
            == "team_players_team_id_jersey_number_key"
        ):
            raise HTTPException(
                status_code=409,
                detail="Ese numero ya esta registrado en este equipo"
            )
            
        if (
            constraint
            == "team_players_team_id_player_id_key"
        ):
            raise HTTPException(
                status_code=409,
                detail="Este jugador ya esta registrado en este equipo"
            )
        raise


@router.post("/import", status_code=201)
async def import_team_roster(
    team_id: int,
    file: UploadFile = File(...),
    _user=Depends(require_team_manager)
):
    """Import several roster players from a CSV or XLSX file."""
    team = get_team_by_id(team_id)

    if team is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    if not file.filename:
        raise HTTPException(status_code=415, detail="Se requiere un archivo .csv o .xlsx")

    content = await file.read(MAX_ROSTER_IMPORT_BYTES + 1)
    if len(content) > MAX_ROSTER_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="El archivo excede 5 MB")

    try:
        players = parse_roster_file(file.filename, content)
        imported = import_players(team, players)
    except RosterImportError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except PlayerAlreadyRegisteredInDivision:
        raise HTTPException(
            status_code=409,
            detail="Uno de los jugadores ya esta registrado en esta rama y categoria"
        )
    except UniqueViolation as error:
        constraint = error.diag.constraint_name
        if constraint == "team_players_team_id_jersey_number_key":
            raise HTTPException(
                status_code=409,
                detail="Uno de los numeros ya esta registrado en este equipo"
            )
        if constraint == "team_players_team_id_player_id_key":
            raise HTTPException(
                status_code=409,
                detail="Uno de los jugadores ya esta registrado en este equipo"
            )
        raise

    return {"imported": len(imported), "rows": imported}


@router.get("/import/template.csv")
def download_roster_template(_user=Depends(require_team_manager)):
    """Provide the canonical columns accepted by CSV and XLSX imports."""
    return Response(
        content="\ufeff" + ROSTER_CSV_TEMPLATE,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="plantilla-roster.csv"'
        }
    )


@router.put("/{player_id}/photo", status_code=204)
async def upload_roster_player_photo(
    team_id: int,
    player_id: int,
    file: UploadFile = File(...),
    _user=Depends(require_team_manager)
):
    """Allow a team manager to complete or replace a roster player's photo."""
    photo = await save_profile_photo(file)
    if not update_roster_player_photo(team_id, player_id, photo):
        raise HTTPException(status_code=404, detail="Jugador no encontrado en este equipo")

@router.get("")
def list_players(team_id: int):
    """Return the public roster for a team."""
    return get_players_by_team(team_id)
