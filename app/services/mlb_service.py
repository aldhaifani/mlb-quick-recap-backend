from datetime import datetime, date
from typing import List, Optional, Dict
from app.core.config import get_settings
from app.services.http_client import HTTPClient
from app.services.cache_service import RedisCache
from app.constants import GameType, Sport, CACHE_EXPIRATION
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class MLBService:
    def __init__(self):
        self.stats_client = HTTPClient(settings.MLB_API_BASE_URL)
        self.gumbo_client = HTTPClient(settings.MLB_GUMBO_API_BASE_URL)
        self.cache = RedisCache()

    async def get_schedule(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        team_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[Dict]:
        cache_key = self.cache.generate_key(
            "schedule", start_date, end_date, team_id, limit
        )

        # Try to get from cache first
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            return cached_data

        # If not in cache, fetch from API
        data = await self._fetch_schedule(start_date, end_date, team_id, limit)

        # Store in cache
        await self.cache.set(cache_key, data, CACHE_EXPIRATION)

        return data

    async def get_game_data(self, game_pk: str) -> Dict:
        cache_key = self.cache.generate_key("game", game_pk)

        # Try to get from cache first
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            return cached_data

        # If not in cache, fetch from API
        data = await self._fetch_game_data(game_pk)

        # Store in cache
        await self.cache.set(cache_key, data, CACHE_EXPIRATION)

        return data

    async def _fetch_schedule(
        self,
        start_date: Optional[date],
        end_date: Optional[date],
        team_id: Optional[int],
        limit: int,
    ) -> List[Dict]:
        params = {
            "sportId": Sport.MLB.value,
            "gameType": GameType.REGULAR,
            "hydrate": "team,venue",
            "limit": limit,
        }

        if start_date:
            params["startDate"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["endDate"] = end_date.strftime("%Y-%m-%d")
        if team_id:
            params["teamId"] = team_id

        response = await self.stats_client.get("schedule", params)
        return self._process_schedule_response(response)

    async def _fetch_game_data(self, game_pk: str) -> Dict:
        response = await self.gumbo_client.get(f"game/{game_pk}/feed/live")
        return self._process_game_response(response)

    # ... rest of the methods remain the same ...
