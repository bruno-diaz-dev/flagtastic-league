"""HTTP endpoints for scheduling games and recording final scores."""

from fastapi import APIRouter, Depends, HTTPException
from models import GameCreate, GameScoreUpdate
from repositories.games import (
    create_game as create_game_repository,
    get_games,
    update_game_score
    )
from repositories.teams import get_team_by_id
from dependencies.auth import require_league_admin

router = APIRouter(
    prefix="/api/games",
    tags=["games"]
)

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


    return create_game_repository(game)


@router.get("")
def list_games():
    """Return all scheduled games and their current scores."""
    return get_games()

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
    
    game = update_game_score(game_id, score)

    if game is None:
        raise HTTPException(
            status_code=404,
            detail="Game not found"
        )

    return game
