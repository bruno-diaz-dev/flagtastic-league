"""FastAPI application assembly and server-rendered page routes."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import get_connection
from observability import RequestObservabilityMiddleware, configure_observability

from routes.teams import router as teams_router
from routes.players import router as players_router
from routes.games import router as games_router
from routes.standings import router as standings_router
from routes.auth import router as auth_router
from routes.statistics import router as statistics_router
from routes.dashboard import router as dashboard_router
from routes.admin import router as admin_router
from routes.referees import router as referees_router

logger = configure_observability()

app = FastAPI(
    title="Flagtastic Football League"
)
app.add_middleware(RequestObservabilityMiddleware, logger=logger)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(directory="templates")

app.include_router(teams_router)
app.include_router(players_router)
app.include_router(games_router)
app.include_router(standings_router)
app.include_router(auth_router)
app.include_router(statistics_router)
app.include_router(dashboard_router)
app.include_router(admin_router)
app.include_router(referees_router)


@app.get("/media/profiles/{filename}")
def profile_photo(filename: str):
    """Serve persistent profile media without exposing database access."""
    connection = get_connection()
    row = connection.execute(
        """
        SELECT profile_photo_data, profile_photo_type
        FROM players WHERE profile_photo_path = %s
        UNION ALL
        SELECT profile_photo_data, profile_photo_type
        FROM users WHERE profile_photo_path = %s
        LIMIT 1
        """,
        (filename, filename)
    ).fetchone()
    connection.close()
    if row is None or row["profile_photo_data"] is None:
        return Response(status_code=404)
    return Response(
        content=bytes(row["profile_photo_data"]),
        media_type=row["profile_photo_type"] or "application/octet-stream",
        headers={
            # Generated filenames change whenever a photo is replaced.
            "Cache-Control": "public, max-age=31536000, immutable",
            "CDN-Cache-Control": "public, max-age=31536000",
            "Vercel-CDN-Cache-Control": "public, max-age=31536000"
        }
    )

@app.get("/")
def index():
    """Redirect the application root to the default operations page."""
    return RedirectResponse("/teams")

@app.get("/live")
def liveness():
    """Expose a dependency-free process liveness check."""
    return JSONResponse(
        content={"status": "alive"},
        headers={"Cache-Control": "no-store"}
    )


@app.get("/ready")
def readiness():
    """Report whether the application can reach its required database."""
    connection = None
    try:
        connection = get_connection()
        connection.execute("SELECT 1").fetchone()
    except Exception as error:
        logger.warning(
            "application.readiness.failed",
            extra={"status_code": 503, "error_type": type(error).__name__}
        )
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable"},
            headers={"Cache-Control": "no-store"}
        )
    finally:
        if connection is not None:
            connection.close()
    return JSONResponse(
        content={"status": "ready"},
        headers={"Cache-Control": "no-store"}
    )

@app.get("/teams")
def teams_page(request: Request):
    """Render the searchable team directory."""
    return templates.TemplateResponse(
        request,
        "teams.html"
    )

@app.get("/games")
def games_page(request: Request):
    """Render the game and score operations page."""
    return templates.TemplateResponse(
        request,
        "games.html"
    )


@app.get("/games/{game_id}")
def game_detail_page(request: Request, game_id: int):
    """Render one game's public shell with role-scoped private sections."""
    return templates.TemplateResponse(
        request=request,
        name="game_detail.html",
        context={"game_id": game_id}
    )

@app.get("/standings")
def standings_page(request: Request):
    """Render the standings query page."""
    return templates.TemplateResponse(
        request,
        "standings.html"
    )


@app.get("/teams/{team_id}/roster")
def roster_page(request: Request, team_id: int):
    """Render one team's public roster and authorized management controls."""
    return templates.TemplateResponse(
        request=request,
        name="roster.html",
        context={"team_id": team_id}
    )


@app.get("/teams/{team_id}/manage")
def team_management_page(request: Request, team_id: int):
    """Render one team's league-administration change center."""
    return templates.TemplateResponse(
        request=request,
        name="team_manage.html",
        context={"team_id": team_id}
    )


@app.get("/statistics")
def statistics_page(request: Request):
    """Render the public individual-statistics leaderboards."""
    return templates.TemplateResponse(request, "statistics.html")


@app.get("/login")
def login_page(request: Request):
    """Render the authentication form for operational users."""
    return templates.TemplateResponse(request, "login.html")


@app.get("/forgot-password")
def forgot_password_page(request: Request):
    """Render the public password reset request form."""
    return templates.TemplateResponse(request, "forgot_password.html")


@app.get("/reset-password")
def reset_password_page(request: Request):
    """Render the one-time password replacement form."""
    return templates.TemplateResponse(request, "reset_password.html")


@app.get("/register")
def register_page(request: Request):
    """Render player self-registration."""
    return templates.TemplateResponse(request, "register.html")


@app.get("/privacy")
def privacy_page(request: Request):
    """Render the public integral privacy notice."""
    return templates.TemplateResponse(request, "privacy.html")


@app.get("/change-password")
def change_password_page(request: Request):
    """Render the password replacement form used on first staff login."""
    return templates.TemplateResponse(request, "change_password.html")


@app.get("/dashboard")
def dashboard_page(request: Request):
    """Render the authenticated player's personal dashboard."""
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/representative-dashboard")
def representative_dashboard_page(request: Request):
    """Render the private representative operations dashboard."""
    return templates.TemplateResponse(request, "representative_dashboard.html")


@app.get("/players/{player_id}")
def public_player_profile_page(request: Request, player_id: int):
    """Render a read-only public player season profile."""
    return templates.TemplateResponse(
        request=request,
        name="player_profile.html",
        context={"player_id": player_id}
    )


@app.get("/admin/users")
def user_administration_page(request: Request):
    """Render role administration; the API enforces actual access."""
    return templates.TemplateResponse(request, "admin_users.html")


@app.get("/referee/games")
def referee_games_page(request: Request):
    """Render the private schedule shell; its API enforces referee access."""
    return templates.TemplateResponse(request, "referee_games.html")


@app.get("/referees")
def referee_roster_page(request: Request):
    """Render the authenticated league referee directory shell."""
    return templates.TemplateResponse(request, "referees.html")
