from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.mlb_api import MLBAPIClient
from app.services.recap_service import RecapService

router = APIRouter()
mlb_client = MLBAPIClient()
recap_service = RecapService()


@router.get("/games/{game_id}/recap")
async def get_game_recap(game_id: int, language: Optional[str] = "en"):
    """Get a natural language recap of a specific game with optional translation."""
    try:
        # Get game details
        games = await mlb_client.get_games()
        game = next((g for g in games.games if g.id == game_id), None)

        if not game:
            raise HTTPException(
                status_code=404, detail=f"Game not found with ID: {game_id}"
            )

        # Get game statistics
        game_stats = await mlb_client.get_game_stats(game_id)
        if not game_stats:
            raise HTTPException(
                status_code=404,
                detail=f"Game statistics not found for game ID: {game_id}",
            )

        # Generate recap
        recap = await recap_service.generate_recap(
            game=game, game_stats=game_stats, target_language=language
        )

        if not recap:
            raise HTTPException(status_code=500, detail="Failed to generate game recap")

        return {"recap": recap}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
