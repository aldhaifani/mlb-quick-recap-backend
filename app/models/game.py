from pydantic import BaseModel
from typing import List
from datetime import datetime


class GameSummary(BaseModel):
    en: str
    es: str
    ja: str


class GameEvent(BaseModel):
    inning: str
    title: str
    description: str


class Game(BaseModel):
    id: str
    date: datetime
    venue: str
    awayTeam: str
    homeTeam: str
    awayScore: int
    homeScore: int
    awayHits: int
    homeHits: int
    awayErrors: int
    homeErrors: int
    topPerformer: str
    winningPitcher: str
    summary: GameSummary
    events: List[GameEvent]


class GameList(BaseModel):
    games: List[Game]
    page: int
    total: int
    has_more: bool
