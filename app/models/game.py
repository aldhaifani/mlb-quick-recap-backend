from pydantic import BaseModel
from typing import List
from datetime import date


class GameEvent(BaseModel):
    inning: str
    title: str
    description: str


class GameSummary(BaseModel):
    en: str
    es: str
    ja: str


class Game(BaseModel):
    id: str
    date: date
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
