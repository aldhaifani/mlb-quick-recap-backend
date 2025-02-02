from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from datetime import datetime, timedelta
from app.services.mlb_service import MLBService
from app.constants import MLB_TEAMS, GAMES_PER_PAGE
from app.models.game import Game, GameList
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_mlb_service():
    return MLBService()


@router.get("/games", response_model=GameList)
async def get_games(
    page: int = Query(1, ge=1, description="Page number"),
    team: Optional[str] = Query(None, description="Team name or abbreviation"),
    mlb_service: MLBService = Depends(get_mlb_service),
):
    """
    Get a list of recent MLB games with optional team filter.
    """
    try:
        # Calculate date range based on page
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7 * page)

        # Convert team name to team ID if provided
        team_id = None
        if team:
            team_upper = team.upper()
            # Try to match by abbreviation first
            team_id = MLB_TEAMS.get(team_upper)

            if not team_id:
                # Try to match by full name
                team_id = next(
                    (id for abbr, id in MLB_TEAMS.items() if team.upper() in abbr), None
                )

            if not team_id:
                raise HTTPException(status_code=404, detail=f"Team '{team}' not found")

        games = await mlb_service.get_schedule(
            start_date=start_date,
            end_date=end_date,
            team_id=team_id,
            limit=GAMES_PER_PAGE,
        )

        return GameList(
            games=games,
            page=page,
            total=len(games),
            has_more=len(games) == GAMES_PER_PAGE,
        )

    except Exception as e:
        logger.error(f"Error fetching games: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching games data")


@router.get("/games/{game_id}", response_model=Game)
async def get_game_details(
    game_id: str, mlb_service: MLBService = Depends(get_mlb_service)
):
    """
    Get detailed information about a specific game.
    """
    try:
        game_data = await mlb_service.get_game_data(game_id)
        return Game(**game_data)
    except Exception as e:
        logger.error(f"Error fetching game {game_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching game data for ID: {game_id}"
        )


@router.get("/teams")
async def get_teams():
    """
    Get list of all MLB teams and their IDs.
    """
    return {
        abbr: {
            "id": team_id,
            "abbreviation": abbr,
        }
        for abbr, team_id in MLB_TEAMS.items()
    }
