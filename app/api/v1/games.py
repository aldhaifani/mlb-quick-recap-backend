from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from app.services.mlb_api import MLBAPIClient
from app.cache.redis_manager import RedisManager
from app.models.game import GameList

router = APIRouter()
mlb_client = MLBAPIClient()
redis_manager = RedisManager()


@router.get("/games", response_model=GameList)
async def get_games(
    season: int = Query(..., ge=2008, le=2024, description="Season year"),
    team_id: int = Query(..., description="Team ID to filter games"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
):
    """Get all games for a given season and team ID with pagination."""
    try:
        # Check Redis cache first
        cached_games = await redis_manager.get_games(season)
        if cached_games:
            return cached_games

        # If not in cache, fetch from MLB API
        games = await mlb_client.get_games(season, team_id, page, per_page)

        # Cache results
        await redis_manager.set_games(games, season)

        return games
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/games/{game_id}/stats")
async def get_game_stats(game_id: int):
    """Get detailed statistics for a specific game."""
    try:
        # Try to get game stats
        game_stats = await mlb_client.get_game_stats(game_id)
        if not game_stats:
            raise HTTPException(
                status_code=404, detail=f"Game stats not found for game ID: {game_id}"
            )

        return game_stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
