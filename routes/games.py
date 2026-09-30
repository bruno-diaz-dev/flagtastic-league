"""HTTP endpoints for scheduling games and recording final scores."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from models import (
    GameCreate,
    GameScheduleImportConfirmation,
    GameScheduleOcrCellsPayload,
    GameScheduleOcrPayload,
    GameScoreUpdate,
    GameStatusUpdate,
    OfficialPositionUpdate,
    RefereeScheduleConfirmation
)
from repositories.games import (
    GameStateConflictError,
    ScheduleConflictError,
    assign_referee,
    apply_referee_schedule,
    create_game as create_game_repository,
    delete_game as delete_game_repository,
    delete_games_by_week,
    get_game_referees,
    get_games_for_referee,
    get_games,
    import_game_schedule,
    remove_referee,
    update_game_score,
    update_game_status,
    update_games_status_by_week
)
from repositories.teams import get_all_teams, get_team_by_id
from dependencies.auth import (
    optional_authenticated_user,
    require_league_admin,
    require_referee,
    user_has_role
)
from repositories.referees import get_referee_match_candidates
from repositories.users import get_user_by_id
from repositories.statistics import get_game_statistics
from repositories.teams import get_represented_team_ids
from services.referee_schedule_ocr import (
    RefereeScheduleImageError,
    parse_referee_schedule_image
)
from services.game_schedule_import import (
    GameScheduleImportError,
    parse_game_schedule_file,
    parse_game_schedule_image,
    parse_game_schedule_ocr_cells,
    parse_game_schedule_ocr_words,
)
from services.divisions import teams_share_game_division

router = APIRouter(
    prefix="/api/games",
    tags=["games"]
)
MAX_REFEREE_SCHEDULE_BYTES = 10 * 1024 * 1024
MAX_GAME_SCHEDULE_BYTES = 15 * 1024 * 1024

@router.post("", status_code=201)
def create_game(
    game: GameCreate,
    _user=Depends(require_league_admin)
):
    """Create a game after validating both participants."""
    if game.home_team_id == game.away_team_id:
        raise HTTPException(
            status_code=409,
            detail="A team cannot play against itself"
        )

    home_team = get_team_by_id(game.home_team_id)
    away_team = get_team_by_id(game.away_team_id)

    if home_team is None or away_team is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    if not teams_share_game_division(home_team, away_team):
        raise HTTPException(
            status_code=409,
            detail=(
                "Los equipos deben pertenecer a la misma rama y categoria; "
                "U12 permite cruces entre ramas"
            )
        )

    return create_game_repository(game)


@router.get("")
def list_games():
    """Return all scheduled games and their current scores."""
    return get_games()


@router.post("/schedule/analyze")
async def analyze_game_schedule(
    file: UploadFile = File(...),
    _admin=Depends(require_league_admin),
):
    """Parse an image or spreadsheet into an administrator review."""
    content = await file.read(MAX_GAME_SCHEDULE_BYTES + 1)
    if len(content) > MAX_GAME_SCHEDULE_BYTES:
        raise HTTPException(status_code=413, detail="El archivo excede 15 MB")
    filename = file.filename or ""
    if file.content_type in {"image/jpeg", "image/png", "image/webp"}:
        try:
            return parse_game_schedule_image(content, get_all_teams())
        except GameScheduleImportError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
    try:
        return parse_game_schedule_file(filename, content, get_all_teams())
    except GameScheduleImportError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/schedule/analyze-cells")
def analyze_game_schedule_cells(
    payload: GameScheduleOcrCellsPayload,
    _admin=Depends(require_league_admin),
):
    try:
        return parse_game_schedule_ocr_cells(
            payload.week,
            [row.model_dump() for row in payload.rows],
            get_all_teams(),
        )
    except GameScheduleImportError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/schedule/analyze-ocr")
def analyze_game_schedule_ocr(
    payload: GameScheduleOcrPayload,
    _admin=Depends(require_league_admin),
):
    """Match browser-side OCR words against registered league teams."""
    try:
        return parse_game_schedule_ocr_words(
            payload.image_width,
            payload.image_height,
            [word.model_dump() for word in payload.words],
            get_all_teams(),
            recognized_text=payload.recognized_text,
            week_override=payload.week_override,
        )
    except GameScheduleImportError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/schedule/confirm")
def confirm_game_schedule(
    confirmation: GameScheduleImportConfirmation,
    _admin=Depends(require_league_admin),
):
    """Persist only game rows that an administrator reviewed."""
    slots = set()
    teams_by_id = {team["id"]: team for team in get_all_teams()}
    for game in confirmation.games:
        if game.home_team_id == game.away_team_id:
            raise HTTPException(status_code=409, detail="Un equipo no puede jugar contra si mismo")
        home_team = teams_by_id.get(game.home_team_id)
        away_team = teams_by_id.get(game.away_team_id)
        if home_team is None or away_team is None:
            raise HTTPException(status_code=404, detail="Equipo no encontrado")
        if not teams_share_game_division(home_team, away_team):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Los equipos deben pertenecer a la misma rama y categoria; "
                    "U12 permite cruces entre ramas"
                )
            )
        slot = (game.week, game.field_number, game.start_time)
        if slot in slots:
            raise HTTPException(status_code=409, detail="El rol contiene dos partidos en el mismo horario y campo")
        slots.add(slot)
    try:
        return import_game_schedule(confirmation.games)
    except ScheduleConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/{game_id}/details")
def game_details(
    game_id: int,
    user=Depends(optional_authenticated_user)
):
    """Return one game with role-scoped statistics and official assignments."""
    game = next((item for item in get_games() if item["id"] == game_id), None)
    if game is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")

    result = {"game": game}
    if user is None:
        return result

    if user_has_role(user, "league_admin"):
        team_ids = [game["home_team"]["id"], game["away_team"]["id"]]
        result["team_statistics"] = get_game_statistics(game_id, team_ids=team_ids)
    elif user_has_role(user, "team_representative"):
        participant_ids = {game["home_team"]["id"], game["away_team"]["id"]}
        represented_ids = participant_ids.intersection(
            get_represented_team_ids(user["id"])
        )
        if represented_ids:
            result["team_statistics"] = get_game_statistics(
                game_id, team_ids=represented_ids
            )

    if user_has_role(user, "player") and user.get("player_id") is not None:
        rows = get_game_statistics(game_id, player_id=user["player_id"])
        result["my_statistics"] = rows[0] if rows else None

    if any(user_has_role(user, role) for role in ("referee", "league_admin")):
        result["officials"] = get_game_referees(game_id)
    return result


@router.get("/mine/referee")
def list_my_referee_games(user=Depends(require_referee)):
    """Return assignments visible only to the authenticated referee."""
    return get_games_for_referee(user["id"])


@router.post("/referee-schedule/analyze")
async def analyze_referee_schedule(
    file: UploadFile = File(...),
    _admin=Depends(require_league_admin)
):
    """Read an image into proposals that still require administrator review."""
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Se requiere una imagen JPG, PNG o WebP")
    content = await file.read(MAX_REFEREE_SCHEDULE_BYTES + 1)
    if len(content) > MAX_REFEREE_SCHEDULE_BYTES:
        raise HTTPException(status_code=413, detail="La imagen excede 10 MB")
    referees = get_referee_match_candidates()
    try:
        return parse_referee_schedule_image(content, get_games(), referees)
    except RefereeScheduleImageError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/referee-schedule/confirm")
def confirm_referee_schedule(
    confirmation: RefereeScheduleConfirmation,
    admin=Depends(require_league_admin)
):
    """Persist only the assignments an administrator reviewed in the UI."""
    referees = {user["id"]: user for user in get_referee_match_candidates()}
    for assignment in confirmation.assignments:
        positions = [official.position for official in assignment.officials]
        official_ids = [official.user_id for official in assignment.officials]
        if not {"referee", "down_judge"}.issubset(positions):
            raise HTTPException(
                status_code=409,
                detail="Referee y Down Judge son obligatorios"
            )
        if len(positions) != len(set(positions)) or len(official_ids) != len(set(official_ids)):
            raise HTTPException(
                status_code=409,
                detail="No se puede repetir un puesto ni una persona"
            )
        if any(
            official.user_id not in referees
            for official in assignment.officials
        ):
            raise HTTPException(status_code=409, detail="El usuario no es arbitro")
    try:
        apply_referee_schedule(confirmation.assignments, admin["id"])
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"updated": len(confirmation.assignments)}


@router.get("/{game_id}/referees")
def list_game_referees(game_id: int, _admin=Depends(require_league_admin)):
    return get_game_referees(game_id)


@router.put("/{game_id}/referees/{user_id}", status_code=201)
def add_game_referee(
    game_id: int,
    user_id: int,
    assignment: OfficialPositionUpdate,
    admin=Depends(require_league_admin)
):
    referee = get_user_by_id(user_id)
    if referee is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not user_has_role(referee, "referee"):
        raise HTTPException(status_code=409, detail="El usuario no es arbitro")
    if not any(game["id"] == game_id for game in get_games()):
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    try:
        return assign_referee(
            game_id, user_id, assignment.position, admin["id"]
        )
    except Exception as error:
        # The composite key prevents assigning one person to two positions.
        if getattr(getattr(error, "diag", None), "constraint_name", None) == "game_referees_pkey":
            raise HTTPException(
                status_code=409,
                detail="La persona ya tiene otro puesto en este partido"
            ) from error
        raise


@router.delete("/{game_id}/referees/{user_id}", status_code=204)
def delete_game_referee(
    game_id: int,
    user_id: int,
    _admin=Depends(require_league_admin)
):
    if not remove_referee(game_id, user_id):
        raise HTTPException(status_code=404, detail="Asignacion no encontrada")

@router.patch("/{game_id}/score")
def update_score(
    game_id: int,
    score: GameScoreUpdate,
    _user=Depends(require_league_admin)
):
    """Record a non-tied final score for an existing game."""

    if score.home_score == score.away_score:
        raise HTTPException(
            status_code=409,
            detail="A game cannot end in a tie"
        )
    
    try:
        game = update_game_score(game_id, score)
    except GameStateConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    if game is None:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    return game


@router.patch("/{game_id}/status")
def change_game_status(
    game_id: int,
    change: GameStatusUpdate,
    _admin=Depends(require_league_admin),
):
    """Postpone or restore an unplayed game."""
    try:
        game = update_game_status(game_id, change.status)
    except GameStateConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.delete("/week/{week}")
def delete_week_games(week: int, _admin=Depends(require_league_admin)):
    """Delete an entire jornada after explicit administrator confirmation."""
    if week < 1:
        raise HTTPException(status_code=422, detail="Invalid week")
    deleted = delete_games_by_week(week)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="No games found for week")
    return {"deleted": deleted, "week": week}


@router.patch("/week/{week}/status")
def change_week_games_status(
    week: int,
    change: GameStatusUpdate,
    _admin=Depends(require_league_admin),
):
    """Postpone or restore every unplayed game in one jornada."""
    if week < 1:
        raise HTTPException(status_code=422, detail="Invalid week")
    updated = update_games_status_by_week(week, change.status)
    if updated is None:
        raise HTTPException(status_code=404, detail="No games found for week")
    if updated == 0:
        raise HTTPException(
            status_code=409,
            detail="La jornada no tiene partidos pendientes",
        )
    return {"updated": updated, "week": week, "status": change.status}


@router.delete("/{game_id}", status_code=204)
def delete_game(game_id: int, _admin=Depends(require_league_admin)):
    """Delete one game and its dependent operational assignments."""
    if not delete_game_repository(game_id):
        raise HTTPException(status_code=404, detail="Game not found")
