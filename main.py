from fastapi import FastAPI

from database import create_database
from routes.teams import router as teams_router
from routes.players import router as players_router
from routes.games import router as games_router

app = FastAPI(
    title="Flagtastic Football League"
)

create_database()

app.include_router(teams_router)
app.include_router(players_router)
app.include_router(games_router)

@app.get("/live")
def liveness():
    return {
        "status": "alive"
    }