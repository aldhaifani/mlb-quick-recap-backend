from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
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


class GameEvent(BaseModel):
    inning: str
    title: str
    description: str


class Game(BaseModel):
    id: int
    game_type: MLBGameType
    date: datetime
    status: GameStatus
    teams: dict[str, Team]
    score: GameScore
    venue: str
    away_hits: Optional[int] = None
    home_hits: Optional[int] = None
    away_errors: Optional[int] = None
    home_errors: Optional[int] = None
    top_performer: Optional[str] = None
    winning_pitcher: Optional[str] = None
    summary: Optional[Dict[str, str]] = Field(
        default=None,
        description="Language code to summary mapping (e.g., {'en': 'English summary', 'es': 'Spanish summary', 'ja': 'Japanese summary'})",
    )
    events: Optional[List[GameEvent]] = None
    cached_at: Optional[datetime] = None


class GameList(BaseModel):
    total_items: int
    games: List[Game]

    @classmethod
    def model_validate(cls, obj):
        if isinstance(obj, dict):
            if "games" in obj and isinstance(obj["games"], list):
                # Convert any tuple to dict before validation
                obj["games"] = [
                    Game.model_validate(
                        dict(
                            zip(
                                [
                                    "id",
                                    "game_type",
                                    "date",
                                    "status",
                                    "teams",
                                    "score",
                                    "venue",
                                    "away_hits",
                                    "home_hits",
                                    "away_errors",
                                    "home_errors",
                                    "top_performer",
                                    "winning_pitcher",
                                    "summary",
                                    "events",
                                    "cached_at",
                                ],
                                game
                                if isinstance(game, tuple)
                                else game.dict()
                                if isinstance(game, Game)
                                else game.items()
                                if isinstance(game, dict)
                                else [],
                            )
                        )
                    )
                    for game in obj["games"]
                ]
        return super().model_validate(obj)
