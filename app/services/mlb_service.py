from datetime import datetime, date
from typing import List, Optional, Dict
from app.core.config import get_settings
from app.services.http_client import HTTPClient
from app.constants import GameType, Sport
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class MLBService:
    def __init__(self):
        self.stats_client = HTTPClient(settings.MLB_API_BASE_URL)
        self.gumbo_client = HTTPClient(settings.MLB_GUMBO_API_BASE_URL)

    async def get_schedule(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        team_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Fetch MLB schedule within the specified date range
        """
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

        try:
            response = await self.stats_client.get("schedule", params)
            return self._process_schedule_response(response)
        except Exception as e:
            logger.error(f"Error fetching schedule: {str(e)}")
            raise

    async def get_game_data(self, game_pk: str) -> Dict:
        """
        Fetch detailed game data using GUMBO API
        """
        try:
            response = await self.gumbo_client.get(f"game/{game_pk}/feed/live")
            return self._process_game_response(response)
        except Exception as e:
            logger.error(f"Error fetching game data: {str(e)}")
            raise

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
        }
