"""HTTP endpoints for Excel imports and public player statistics."""

from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook

from repositories.statistics import (
    StatisticsValidationError,
    get_week_statistics,
    get_leaderboards,
    get_player_statistics,
    import_statistics_workbook,
    import_week_statistics
)
from services.statistics_import import (
    StatisticsFileError,
    parse_games_workbook,
    parse_statistics_workbook
)
from dependencies.auth import require_league_admin


router = APIRouter(tags=["statistics"])
MAX_WORKBOOK_BYTES = 15 * 1024 * 1024


@router.get("/api/statistics/import-template")
def statistics_import_template(_user=Depends(require_league_admin)):
    """Download the canonical workbook headers used by weekly imports."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Estadisticas"
    sheet.append([
        "rama",
        "categoria",
        "equipo",
        "numero",
        "puntos",
        "recepciones",
        "intercepciones",
        "capturas",
        "tacleadas",
        "pases_completos",
        "pases_lanzados"
    ])
    content = BytesIO()
    workbook.save(content)
    workbook.close()
    content.seek(0)
    return StreamingResponse(
        content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                'attachment; filename="plantilla-estadisticas-flagtastic.xlsx"'
            )
        }
    )


@router.post("/api/weeks/{week}/player-stats/import")
async def import_statistics(
    week: int,
    file: UploadFile = File(...),
    _user=Depends(require_league_admin)
):
    """Replace a complete week's statistics from one validated workbook."""
    if week < 1:
        raise HTTPException(status_code=422, detail="La jornada debe ser mayor a cero")
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=415, detail="Se requiere un archivo .xlsx")

    content = await file.read(MAX_WORKBOOK_BYTES + 1)
    if len(content) > MAX_WORKBOOK_BYTES:
        raise HTTPException(status_code=413, detail="El archivo excede 5 MB")

    try:
        weeks = parse_statistics_workbook(content, selected_week=week)
        try:
            games = parse_games_workbook(content, selected_week=week)
        except StatisticsFileError:
            # The legacy compact template has statistics but no game blocks.
            games = None
        imported = import_week_statistics(
            week,
            weeks[week],
            games[week] if games is not None else None
        )
    except (StatisticsFileError, StatisticsValidationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return {"imported": len(imported), "rows": imported}


@router.post("/api/statistics/import")
async def import_official_statistics(
    file: UploadFile = File(...),
    _user=Depends(require_league_admin)
):
    """Import every `Wk` sheet found in the official league workbook."""
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=415, detail="Se requiere un archivo .xlsx")
    content = await file.read(MAX_WORKBOOK_BYTES + 1)
    if len(content) > MAX_WORKBOOK_BYTES:
        raise HTTPException(status_code=413, detail="El archivo excede 15 MB")
    try:
        weeks = parse_statistics_workbook(content)
        games = parse_games_workbook(content)
        imported = import_statistics_workbook(weeks, games)
    except (StatisticsFileError, StatisticsValidationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {
        "weeks": sorted(weeks),
        "imported": len(imported),
        "games": sum(len(rows) for rows in games.values()),
        "rows": imported
    }


@router.get("/api/weeks/{week}/player-stats")
def list_week_statistics(week: int):
    """Return individual statistics recorded for a complete week."""
    if week < 1:
        raise HTTPException(status_code=422, detail="La jornada debe ser mayor a cero")
    return get_week_statistics(week)


@router.get("/api/players/{player_id}/stats")
def player_statistics(player_id: int):
    """Return a player's totals derived from weekly records."""
    statistics = get_player_statistics(player_id)
    if statistics is None:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    return statistics


@router.get("/api/statistics/leaderboards")
def statistics_leaderboards(branch: str, category: str):
    """Return five leaders per statistic for one division."""
    return get_leaderboards(branch, category)
