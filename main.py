"""FastAPI application assembly and server-rendered page routes."""

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import get_connection

from routes.teams import router as teams_router
from routes.players import router as players_router
from routes.games import router as games_router
from routes.standings import router as standings_router
from routes.auth import router as auth_router
from routes.statistics import router as statistics_router
from routes.dashboard import router as dashboard_router
from routes.admin import router as admin_router

app = FastAPI(
    title="Flagtastic Football League"
)

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


@app.get("/media/profiles/{filename}")
def profile_photo(filename: str):
    """Serve persistent profile media without exposing database access."""
    connection = get_connection()
    row = connection.execute(
        """
        SELECT profile_photo_data, profile_photo_type
        FROM players WHERE profile_photo_path = %s
        """,
        (filename,)
    ).fetchone()
    connection.close()
    if row is None or row["profile_photo_data"] is None:
        return Response(status_code=404)
    return Response(
        content=bytes(row["profile_photo_data"]),
        media_type=row["profile_photo_type"] or "application/octet-stream"
    )

@app.get("/")
def index():
    """Redirect the application root to the default operations page."""
    return RedirectResponse("/teams")

@app.get("/live")
def liveness():
    """Expose a dependency-free process liveness check."""
    return {
        "status": "alive"
    }

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


@app.get("/statistics")
def statistics_page(request: Request):
    """Render the public individual-statistics leaderboards."""
    return templates.TemplateResponse(request, "statistics.html")


@app.get("/login")
def login_page(request: Request):
    """Render the authentication form for operational users."""
    return templates.TemplateResponse(request, "login.html")


@app.get("/register")
def register_page(request: Request):
    """Render player self-registration."""
    return templates.TemplateResponse(request, "register.html")


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
