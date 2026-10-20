"""HTTP endpoints for Excel imports and public player statistics."""

from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
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
from repositories.dashboard import get_player_dashboard
from services.statistics_import import (
    StatisticsFileError,
    parse_games_workbook,
    parse_statistics_workbook
)
from dependencies.auth import require_league_admin
from models import ALLOWED_BRANCHES, ALLOWED_CATEGORIES
from services.divisions import category_allows_cross_branch_games


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
    existing_records: Literal["preserve", "update"] = Form("update"),
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

    warnings = []
    try:
        weeks = parse_statistics_workbook(content, selected_week=week, warnings=warnings)
        try:
            games = parse_games_workbook(content, selected_week=week)
        except StatisticsFileError:
            # The legacy compact template has statistics but no game blocks.
            games = None
        imported = import_week_statistics(
            week,
            weeks[week],
            games[week] if games is not None else None,
            existing_records=existing_records
        )
    except (StatisticsFileError, StatisticsValidationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return {**imported, "warnings": warnings}


@router.post("/api/weeks/{week}/player-stats/import-division")
async def import_division_statistics(
    week: int,
    branch: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...),
    existing_records: Literal["preserve", "update"] = Form("update"),
    _user=Depends(require_league_admin),
):
    """Replace just one division of a week, leaving other divisions intact."""
    branch = branch.strip().lower()
    category = category.strip().lower()
    if week < 1:
        raise HTTPException(status_code=422, detail="La jornada debe ser mayor a cero")
    if branch not in ALLOWED_BRANCHES or category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=422, detail="Rama o categoría inválida")
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=415, detail="Se requiere un archivo .xlsx")

    content = await file.read(MAX_WORKBOOK_BYTES + 1)
    if len(content) > MAX_WORKBOOK_BYTES:
        raise HTTPException(status_code=413, detail="El archivo excede 15 MB")
    warnings = []
    try:
        weeks = parse_statistics_workbook(content, selected_week=week, warnings=warnings)
        rows = weeks[week]
        if any(
            row["category"] != category
            or (
                not category_allows_cross_branch_games(category)
                and row["branch"] != branch
            )
            for row in rows
        ):
            raise StatisticsFileError(
                "El archivo contiene otras categorías o ramas. "
                "Usa Archivo completo o selecciona la división correcta."
            )
        # Official Wk or Hoja1 blocks identify individual games, including
        # doubleheaders. Compact files have no game blocks and remain valid.
        try:
            games = parse_games_workbook(content, selected_week=week)
        except StatisticsFileError as error:
            if str(error) != "El archivo no contiene partidos por jornada":
                raise
            games = None
        imported = import_week_statistics(
            week, rows,
            games[week] if games else None,
            link_existing_games_only=True,
            existing_records=existing_records,
        )
    except (StatisticsFileError, StatisticsValidationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"weeks": [week], **imported, "warnings": warnings}


@router.post("/api/statistics/import")
async def import_official_statistics(
    file: UploadFile = File(...),
    existing_records: Literal["preserve", "update"] = Form("update"),
    _user=Depends(require_league_admin)
):
    """Import every `Wk` sheet found in the official league workbook."""
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=415, detail="Se requiere un archivo .xlsx")
    content = await file.read(MAX_WORKBOOK_BYTES + 1)
    if len(content) > MAX_WORKBOOK_BYTES:
        raise HTTPException(status_code=413, detail="El archivo excede 15 MB")
    warnings = []
    try:
        weeks = parse_statistics_workbook(content, warnings=warnings)
        games = parse_games_workbook(content)
        imported = import_statistics_workbook(weeks, games, existing_records=existing_records)
    except (StatisticsFileError, StatisticsValidationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {
        "weeks": sorted(weeks),
        **imported, "warnings": warnings,
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


@router.get("/api/players/{player_id}/profile")
def public_player_profile(player_id: int):
    """Return the public season profile without account or CURP data."""
    profile = get_player_dashboard(player_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    return profile


@router.get("/api/statistics/leaderboards")
def statistics_leaderboards(branch: str, category: str, response: Response):
    """Return five leaders per statistic for one division."""
    response.headers["Cache-Control"] = "public, max-age=0, must-revalidate"
    response.headers["Vercel-CDN-Cache-Control"] = "public, max-age=60"
    return get_leaderboards(branch, category)
