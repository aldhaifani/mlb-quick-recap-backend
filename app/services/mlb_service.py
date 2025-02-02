from datetime import datetime, date
from typing import List, Optional, Dict
from app.core.config import get_settings
from app.services.http_client import HTTPClient
from app.services.cache_service import RedisCache
from app.services.ai_service import AIService
from app.services.translation_service import TranslationService
from app.constants import GameType, Sport, CACHE_EXPIRATION
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class MLBService:
    def __init__(self):
        self.stats_client = HTTPClient(settings.MLB_API_BASE_URL)
        self.gumbo_client = HTTPClient(settings.MLB_GUMBO_API_BASE_URL)
        self.cache = RedisCache()
        self.ai_service = AIService()
        self.translation_service = TranslationService()

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

        # If not in cache, fetch from API and generate recap
        data = await self._fetch_game_data(game_pk)

        # Generate English recap
        recap = await self.ai_service.generate_game_recap(data)

        # Translate recap
        translations = await self.translation_service.translate_recap(
            recap, settings.GOOGLE_CLOUD_PROJECT
        )

        # Add translations to data
        data["summary"] = translations

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

    def _process_schedule_response(self, response: Dict) -> List[Dict]:
        """
        Process and filter schedule response
        """
        if not response.get("dates"):
            return []

        games = []
        for date_data in response["dates"]:
            for game in date_data["games"]:
                # Only include games from 2008 onwards
                game_date = datetime.strptime(game["gameDate"], "%Y-%m-%dT%H:%M:%SZ")
                if game_date.year >= settings.MLB_DATA_START_YEAR:
                    games.append(
                        {
                            "id": str(game["gamePk"]),
                            "date": game["gameDate"],
                            "teams": {
                                "away": game["teams"]["away"]["team"]["name"],
                                "home": game["teams"]["home"]["team"]["name"],
                            },
                            "status": game["status"]["detailedState"],
                        }
                    )

        return games

    def _process_game_response(self, response: Dict) -> Dict:
        """
        Process GUMBO API response
        """
        game_data = response["gameData"]
        live_data = response["liveData"]

        return {
            "id": str(game_data["game"]["pk"]),
            "date": game_data["datetime"]["dateTime"],
            "venue": game_data["venue"]["name"],
            "awayTeam": game_data["teams"]["away"]["name"],
            "homeTeam": game_data["teams"]["home"]["name"],
            "awayScore": live_data["linescore"]["teams"]["away"]["runs"],
            "homeScore": live_data["linescore"]["teams"]["home"]["runs"],
            "awayHits": live_data["linescore"]["teams"]["away"]["hits"],
            "homeHits": live_data["linescore"]["teams"]["home"]["hits"],
            "awayErrors": live_data["linescore"]["teams"]["away"]["errors"],
            "homeErrors": live_data["linescore"]["teams"]["home"]["errors"],
            "plays": live_data["plays"]["allPlays"],
            "boxscore": live_data["boxscore"],
            "topPerformer": self._determine_top_performer(live_data),
            "winningPitcher": self._get_winning_pitcher(live_data),
        }

    def _determine_top_performer(self, live_data: Dict) -> str:
        """
        Determine the top performer based on game stats
        """
        try:
            # This is a simplified version - you might want to implement more sophisticated logic
            home_stats = live_data["boxscore"]["teams"]["home"]["players"]
            away_stats = live_data["boxscore"]["teams"]["away"]["players"]
            all_players = {**home_stats, **away_stats}

            top_performer = None
            max_impact = 0

            for player_id, stats in all_players.items():
                if "stats" not in stats:
                    continue

                batting = stats.get("stats", {}).get("batting", {})
                pitching = stats.get("stats", {}).get("pitching", {})

                # Calculate player impact (simplified)
                impact = (
                    batting.get("hits", 0) * 1
                    + batting.get("homeRuns", 0) * 4
                    + batting.get("rbi", 0) * 1
                    + pitching.get("strikeOuts", 0) * 0.5
                )

                if impact > max_impact:
                    max_impact = impact
                    top_performer = stats["person"]["fullName"]

            return top_performer or "Not Available"

        except Exception as e:
            logger.error(f"Error determining top performer: {str(e)}")
            return "Not Available"

    def _get_winning_pitcher(self, live_data: Dict) -> str:
        """
        Get the winning pitcher's name
        """
        try:
            decisions = live_data.get("decisions", {})
            if winner_id := decisions.get("winner", {}).get("id"):
                home_players = live_data["boxscore"]["teams"]["home"]["players"]
                away_players = live_data["boxscore"]["teams"]["away"]["players"]
                all_players = {**home_players, **away_players}

                winner_key = f"ID{winner_id}"
                if winner := all_players.get(winner_key):
                    return winner["person"]["fullName"]

            return "Not Available"

        except Exception as e:
            logger.error(f"Error getting winning pitcher: {str(e)}")
            return "Not Available"
