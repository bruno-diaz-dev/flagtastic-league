"""Public live game read model and referee-only event capture."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, model_validator

from dependencies.auth import require_referee, require_authenticated_user, user_has_role
from repositories.live_games import LiveGameError, read_live_game, start_live_game, append_event, void_event, finish_live_game

router = APIRouter(prefix="/api/games/{game_id}/live", tags=["live games"])


class LiveEvent(BaseModel):
    """An idempotent, timestamped entry in the digital statistics sheet."""
    client_id: UUID
    kind: Literal["pass_complete", "pass_incomplete", "passing_touchdown", "touchdown", "extra_one", "extra_two", "safety", "sack", "flag", "interception", "attendance", "halftime", "two_minute_warning"]
    team_id: int | None = Field(default=None, gt=0)
    player_id: int | None = Field(default=None, gt=0)
    receiver_id: int | None = Field(default=None, gt=0)
    period: int = Field(ge=1, le=10)
    minute: int = Field(ge=0, le=200)
    second: int = Field(ge=0, le=59)
    note: Literal[""] = ""  # Compatibility with stored payloads; narration is automatic.

    @model_validator(mode="after")
    def validate_players(self):
        if self.kind in ("halftime", "two_minute_warning"):
            if any(value is not None for value in (self.team_id, self.player_id, self.receiver_id)):
                raise ValueError("Las pausas corresponden al partido, sin equipo ni jugador")
            return self
        if self.team_id is None:
            raise ValueError("Selecciona al equipo")
        if self.player_id is None:
            raise ValueError("Selecciona al jugador de la jugada")
        is_pass = self.kind in ("pass_complete", "passing_touchdown")
        if is_pass and (self.receiver_id is None or self.receiver_id == self.player_id):
            raise ValueError("Selecciona un receptor distinto al pasador")
        if not is_pass and self.receiver_id is not None:
            raise ValueError("Esta jugada no requiere receptor")
        return self


class LiveFinish(BaseModel):
    expected_version: int = Field(ge=0)


class LiveVoid(BaseModel):
    reason: str = Field(min_length=3, max_length=160)
    expected_version: int = Field(ge=0)


def perform(operation, *args):
    """Translate domain conflicts without leaking database errors."""
    try:
        return operation(*args)
    except LiveGameError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@router.get("")
def live_snapshot(game_id: int, response: Response):
    """Expose only game, sporting identities and published play events."""
    response.headers["Cache-Control"] = "public, max-age=0, must-revalidate"
    response.headers["Vercel-CDN-Cache-Control"] = "public, max-age=5"
    return perform(read_live_game, game_id)


@router.post("/start")
def start(game_id: int, user=Depends(require_referee)):
    return perform(start_live_game, game_id, user["id"])


@router.post("/events", status_code=201)
def capture(game_id: int, event: LiveEvent, user=Depends(require_referee)):
    return perform(append_event, game_id, event.model_dump(), user["id"])


@router.post("/events/{event_id}/void")
def correct(game_id: int, event_id: int, correction: LiveVoid, user=Depends(require_authenticated_user)):
    if not any(user_has_role(user, role) for role in ("referee", "league_admin")):
        raise HTTPException(status_code=403, detail="Acceso no autorizado")
    return perform(void_event, game_id, event_id, correction.model_dump(), user["id"], user_has_role(user, "league_admin"), user_has_role(user, "referee"))


@router.post("/finish")
def finish(game_id: int, payload: LiveFinish, user=Depends(require_referee)):
    return perform(finish_live_game, game_id, payload.expected_version, user["id"])
