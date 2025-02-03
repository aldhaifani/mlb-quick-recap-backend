from typing import Optional, Any
from datetime import datetime
import json
from redis import Redis
from app.config import settings
from app.models.game import Game, GameList


class RedisManager:
    _instance = None
    _redis: Optional[Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._redis:
            self._redis = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                ssl=settings.REDIS_SSL,
                decode_responses=True,
            )

    async def get_games(self, season: int, team: str) -> Optional[GameList]:
        """Retrieve games from cache based on season and team filter."""
        cache_key = self._generate_cache_key(season, team)
        data = self._redis.get(cache_key)

        if not data:
            return None

        try:
            game_data = json.loads(data)
            return GameList(**game_data)
        except Exception:
            return None

    async def set_games(self, games: GameList, season: int, team: str) -> bool:
        """Store games in cache with the specified TTL."""
        cache_key = self._generate_cache_key(season, team)
        try:
            # Update cached_at timestamp for each game
            for game in games.games:
                game.cached_at = datetime.utcnow()

            # Store in Redis with TTL
            return self._redis.setex(
                cache_key, settings.CACHE_TTL, json.dumps(games.dict())
            )
        except Exception:
            return False

    def _generate_cache_key(self, season: int, team: str) -> str:
        """Generate a unique cache key based on season and team filter."""
        return f"games:season:{season}:team:{team}"
