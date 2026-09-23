"""FastAPI application assembly and server-rendered page routes."""

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routes.teams import router as teams_router
from routes.players import router as players_router
from routes.games import router as games_router
from routes.standings import router as standings_router
from routes.auth import router as auth_router

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
    """Render the team and roster operations page."""
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

@app.get("/standings")
def standings_page(request: Request):
    """Render the standings query page."""
    return templates.TemplateResponse(
        request,
        "standings.html"
    )
