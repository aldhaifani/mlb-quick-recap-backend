from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.config import MLBGameType


class Team(BaseModel):
    id: int
    name: str
    abbreviation: str


class GameStatus(BaseModel):
    abstract_game_state: str
    detailed_state: str
    status_code: str
    is_final: bool


class GameScore(BaseModel):
    away: int
    home: int


class Game(BaseModel):
    id: int
    game_type: MLBGameType
    date: datetime
    status: GameStatus
    teams: dict[str, Team]
    score: GameScore
    venue: str
    recap: Optional[str] = None
    translations: Optional[dict[str, str]] = None
    cached_at: Optional[datetime] = None


class GameList(BaseModel):
    total_items: int
    games: List[Game]
