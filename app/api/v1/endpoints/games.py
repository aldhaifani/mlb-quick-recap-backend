from fastapi import APIRouter, Query
from typing import List, Optional
from app.models.game import Game

router = APIRouter()


@router.get("/games/", response_model=List[Game])
async def get_games(
    page: int = Query(1, ge=1),
    team: Optional[str] = None,
):
    """
    Get a list of games with optional team filter.

    - Without team parameter: Returns latest 10 games
    - With team parameter: Returns latest 10 games for specific team
    - Use page parameter for pagination
    """
    # Implementation will be added in later steps
    pass
