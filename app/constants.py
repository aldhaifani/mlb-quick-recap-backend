from enum import Enum


class GameType(str, Enum):
    REGULAR = "R"
    POSTSEASON = "P"
    SPRING = "S"


class Sport(Enum):
    MLB = 1


MLB_DATE_FORMAT = "YYYY/MM/DD"
CACHE_EXPIRATION = 600  # 10 minutes in seconds
GAMES_PER_PAGE = 10
