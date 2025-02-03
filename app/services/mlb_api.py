from datetime import datetime, timedelta
from typing import Optional, List
import requests
from app.config import settings, MLBGameType
from app.models.game import Game, GameStatus, Team, GameScore, GameList


class MLBAPIClient:
    def __init__(self):
        self.base_url = settings.MLB_API_BASE_URL
        self.gumbo_url = settings.MLB_GUMBO_API_BASE_URL

    async def get_games(self, team: str, season: int) -> GameList:
        """Fetch all games for a specific team in a given season."""
        # Build the API URL with season date range
        url = f"{self.base_url}/schedule"
        params = {
            "sportId": settings.MLB_SPORT_ID,
            "startDate": f"{season}-01-01",
            "endDate": f"{season}-12-31",
            "gameType": MLBGameType.REGULAR,
            "hydrate": "team,venue",
            "teamId": await self._get_team_id(team),
        }

        # Make the API request
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Process and format the response
        games = []
        for date in data.get("dates", []):
            for game_data in date.get("games", []):
                game = await self._process_game(game_data)
                if game:
                    games.append(game)

        return GameList(total_items=len(games), games=games)

    async def _get_team_id(self, team_name: str) -> Optional[int]:
        """Get team ID from team name or abbreviation."""
        url = f"{self.base_url}/teams"
        params = {"sportId": settings.MLB_SPORT_ID}

        response = requests.get(url, params=params)
        response.raise_for_status()

        team_name = team_name.lower()
        for team in response.json().get("teams", []):
            if team_name in [team["name"].lower(), team["abbreviation"].lower()]:
                return team["id"]
        return None

    async def _process_game(self, game_data: dict) -> Optional[Game]:
        """Process raw game data into Game model."""
        try:
            return Game(
                id=game_data["gamePk"],
                game_type=game_data["gameType"],
                date=datetime.strptime(game_data["gameDate"], "%Y-%m-%dT%H:%M:%SZ"),
                status=GameStatus(
                    abstract_game_state=game_data["status"]["abstractGameState"],
                    detailed_state=game_data["status"]["detailedState"],
                    status_code=game_data["status"]["statusCode"],
                    is_final=game_data["status"]["abstractGameState"] == "Final",
                ),
                teams={
                    "away": Team(
                        id=game_data["teams"]["away"]["team"]["id"],
                        name=game_data["teams"]["away"]["team"]["name"],
                        abbreviation=game_data["teams"]["away"]["team"]["abbreviation"],
                    ),
                    "home": Team(
                        id=game_data["teams"]["home"]["team"]["id"],
                        name=game_data["teams"]["home"]["team"]["name"],
                        abbreviation=game_data["teams"]["home"]["team"]["abbreviation"],
                    ),
                },
                score=GameScore(
                    away=game_data["teams"]["away"]["score"],
                    home=game_data["teams"]["home"]["score"],
                ),
                venue=game_data["venue"]["name"],
            )
        except KeyError:
            return None

    async def get_game_details(self, game_id: int) -> Optional[dict]:
        """Fetch detailed game data from MLB GUMBO API."""
        url = f"{self.gumbo_url}/game/{game_id}/feed/live"

        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError):
            return None

    async def get_game_stats(self, game_id: int) -> Optional[dict]:
        """Process and extract relevant game statistics for recap generation."""
        game_data = await self.get_game_details(game_id)
        if not game_data:
            return None

        try:
            live_data = game_data.get("liveData", {})
            linescore = live_data.get("linescore", {})
            boxscore = live_data.get("boxscore", {})
            plays = live_data.get("plays", {})
            decisions = live_data.get("decisions", {})

            # Extract team stats (batting and pitching)
            team_stats = {}
            for team_id, team_data in boxscore.get("teams", {}).items():
                team_batting = team_data.get("teamStats", {}).get("batting", {})
                team_pitching = team_data.get("teamStats", {}).get("pitching", {})

                team_stats[team_id] = {
                    "batting": {
                        "hits": team_batting.get("hits", 0),
                        "runs": team_batting.get("runs", 0),
                        "strikeouts": team_batting.get("strikeOuts", 0),
                        "walks": team_batting.get("baseOnBalls", 0),
                        "avg": team_batting.get("avg", ".000"),
                        "batting_highlights": [],
                    },
                    "pitching": {
                        "strikeouts": team_pitching.get("strikeOuts", 0),
                        "walks": team_pitching.get("baseOnBalls", 0),
                        "earned_runs": team_pitching.get("earnedRuns", 0),
                        "era": team_pitching.get("era", "0.00"),
                        "pitching_highlights": [],
                    },
                }

                # Process individual player stats
                for player_id, player in team_data.get("players", {}).items():
                    # Batting highlights
                    batting_stats = player.get("stats", {}).get("batting", {})
                    if batting_stats.get("hits", 0) > 0:
                        team_stats[team_id]["batting"]["batting_highlights"].append(
                            {
                                "player_name": player.get("person", {}).get(
                                    "fullName", ""
                                ),
                                "hits": batting_stats.get("hits", 0),
                                "home_runs": batting_stats.get("homeRuns", 0),
                                "rbi": batting_stats.get("rbi", 0),
                                "avg": batting_stats.get("avg", ".000"),
                            }
                        )

                    # Pitching highlights
                    pitching_stats = player.get("stats", {}).get("pitching", {})
                    if pitching_stats.get("inningsPitched", 0) > 0:
                        team_stats[team_id]["pitching"]["pitching_highlights"].append(
                            {
                                "player_name": player.get("person", {}).get(
                                    "fullName", ""
                                ),
                                "innings_pitched": pitching_stats.get(
                                    "inningsPitched", "0.0"
                                ),
                                "strikeouts": pitching_stats.get("strikeOuts", 0),
                                "walks": pitching_stats.get("baseOnBalls", 0),
                                "earned_runs": pitching_stats.get("earnedRuns", 0),
                                "era": pitching_stats.get("era", "0.00"),
                            }
                        )

            # Get key moments and plays
            key_plays = []
            for play in plays.get("allPlays", []):
                if play.get("about", {}).get("isComplete", False) and (
                    play.get("result", {}).get("rbi", 0) > 0
                    or play.get("result", {}).get("event")
                    in ["Home Run", "Strikeout", "Walk"]
                ):
                    key_plays.append(
                        {
                            "inning": play.get("about", {}).get("inning"),
                            "half_inning": play.get("about", {}).get("halfInning"),
                            "description": play.get("result", {}).get(
                                "description", ""
                            ),
                            "rbi": play.get("result", {}).get("rbi", 0),
                            "event": play.get("result", {}).get("event"),
                            "batter": play.get("matchup", {})
                            .get("batter", {})
                            .get("fullName"),
                            "pitcher": play.get("matchup", {})
                            .get("pitcher", {})
                            .get("fullName"),
                        }
                    )

            return {
                "linescore": linescore,
                "team_stats": team_stats,
                "scoring_plays": plays.get("scoringPlays", []),
                "key_plays": key_plays,
                "home_runs": plays.get("homeRuns", []),
                "decisions": {
                    "winner": decisions.get("winner", {}).get("fullName"),
                    "loser": decisions.get("loser", {}).get("fullName"),
                    "save": decisions.get("save", {}).get("fullName"),
                },
                "game_info": {
                    "venue": game_data.get("gameData", {}).get("venue", {}).get("name"),
                    "weather": game_data.get("gameData", {}).get("weather", {}),
                    "attendance": game_data.get("gameData", {}).get("attendance"),
                    "game_time": game_data.get("gameData", {})
                    .get("gameInfo", {})
                    .get("gameDurationMinutes"),
                },
            }
        except (KeyError, AttributeError):
            return None
