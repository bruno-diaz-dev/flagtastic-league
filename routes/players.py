"""HTTP endpoints for player registration and team rosters."""

from psycopg.errors import UniqueViolation
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile

from models import PlayerCreate, RegisteredPlayerMembershipCreate, RosterPlayerUpdate
from repositories.teams import get_team_by_id
from repositories.players import (
    create_player,
    deactivate_roster_player,
    get_managed_roster_player,
    import_players,
    join_registered_player,
    search_registered_players,
    get_players_by_team,
    update_roster_player,
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
    "nombre,curp,numero\n"
    "Nombre Completo,ABCD000101HASXXX00,10\n"
)


@router.get("/candidates")
def find_registered_player_candidates(
    team_id: int,
    q: str = Query(min_length=2, max_length=80),
    _user=Depends(require_team_manager)
):
    """Search eligible registered players by legal name or AKA."""
    team = get_team_by_id(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return search_registered_players(team, q)


@router.post("/registered", status_code=201)
def register_existing_player(
    team_id: int,
    membership: RegisteredPlayerMembershipCreate,
    _user=Depends(require_team_manager)
):
    """Add a selected registered player to an eligible managed roster."""
    team = get_team_by_id(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    try:
        created = join_registered_player(
            membership.player_id,
            team,
            membership.jersey_number
        )
    except PlayerAlreadyRegisteredInDivision as error:
        raise HTTPException(
            status_code=409,
            detail="Este jugador ya esta registrado en esta rama y categoria"
        ) from error
    except UniqueViolation as error:
        if error.diag.constraint_name == "team_players_team_id_jersey_number_key":
            raise HTTPException(
                status_code=409,
                detail="Ese numero ya esta registrado en este equipo"
            ) from error
        raise
    if created is None:
        raise HTTPException(status_code=404, detail="Jugador registrado no encontrado")
    return created

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


@router.get("/{player_id}/management")
def get_roster_player_management_fields(
    team_id: int,
    player_id: int,
    _user=Depends(require_team_manager)
):
    """Return private identity fields to an authorized roster manager."""
    player = get_managed_roster_player(team_id, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Jugador no encontrado en este equipo")
    return player


@router.patch("/{player_id}")
def edit_roster_player(
    team_id: int,
    player_id: int,
    payload: RosterPlayerUpdate,
    _user=Depends(require_team_manager)
):
    """Correct an active player's identity and jersey assignment."""
    try:
        updated = update_roster_player(team_id, player_id, payload)
    except UniqueViolation as error:
        constraint = error.diag.constraint_name
        if constraint == "players_curp_key":
            detail = "La CURP ya pertenece a otro jugador"
        elif constraint == "team_players_team_id_jersey_number_key":
            detail = "Ese numero ya esta registrado en este equipo"
        else:
            raise
        raise HTTPException(status_code=409, detail=detail) from error
    if updated is None:
        raise HTTPException(status_code=404, detail="Jugador no encontrado en este equipo")
    return updated


@router.delete("/{player_id}", status_code=204)
def remove_roster_player(
    team_id: int,
    player_id: int,
    _user=Depends(require_team_manager)
):
    """Deactivate a roster membership while preserving player history."""
    if not deactivate_roster_player(team_id, player_id):
        raise HTTPException(status_code=404, detail="Jugador no encontrado en este equipo")

@router.get("")
def list_players(team_id: int):
    """Return the public roster for a team."""
    return get_players_by_team(team_id)
