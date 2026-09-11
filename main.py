from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database import create_database
from routes.teams import router as teams_router
from routes.players import router as players_router
from routes.games import router as games_router
from routes.standings import router as standings_router

app = FastAPI(
    title="Flagtastic Football League"
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

create_database()

app.include_router(teams_router)
app.include_router(players_router)
app.include_router(games_router)
app.include_router(standings_router)

@app.get("/")
def index():
    return FileResponse("templates/index.html")

@app.get("/live")
def liveness():
    return {
        "status": "alive"
    }