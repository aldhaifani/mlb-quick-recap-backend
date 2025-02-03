from datetime import datetime
from typing import Optional
import aiohttp
import asyncio
from app.config import settings
from app.models.game import Game, GameStatus, Team, GameScore, GameList


class MLBAPIClient:
    def __init__(self):
        self.base_url = settings.MLB_API_BASE_URL
        self.gumbo_url = settings.MLB_GUMBO_API_BASE_URL

    async def get_games(
        self, season: int, team_id: int, page: int = 1, per_page: int = 10
    ) -> GameList:
        """Fetch all games for a given season and team ID with pagination."""
        # Build the API URL with season date range
        url = f"{self.base_url}/schedule"
        params = {
            "sportId": settings.MLB_SPORT_ID,
            "startDate": f"{season}-01-01",
            "endDate": f"{season}-12-31",
            "gameType": "R",
            "hydrate": "team,venue,linescore",
            "teamId": team_id,
        }

        # Make the API request
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=30) as response:
                response.raise_for_status()
                data = await response.json()

        # Process and format the response
        game_tasks = []
        for date in data.get("dates", []):
            for game_data in date.get("games", []):
                game_tasks.append(self._process_game(game_data))

        # Process games concurrently
        games = [game for game in await asyncio.gather(*game_tasks) if game]

        # Sort games by date in descending order (latest first)
        games.sort(key=lambda x: x.date, reverse=True)

        # Calculate pagination
        total_items = len(games)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_games = games[start_idx:end_idx]

        return GameList(total_items=total_items, games=paginated_games)

    async def _process_game(self, game_data: dict) -> Optional[Game]:
        """Process raw game data into Game model."""
        try:
            # Get detailed game data from GUMBO API
            game_details = await self.get_game_details(game_data["gamePk"])
            if not game_details:
                return None

            live_data = game_details.get("liveData", {})
            boxscore = live_data.get("boxscore", {})
            plays = live_data.get("plays", {})
            decisions = live_data.get("decisions", {})

            # Get linescore data for hits and errors
            linescore = game_data.get("linescore", {})
            away_hits = linescore.get("teams", {}).get("away", {}).get("hits")
            home_hits = linescore.get("teams", {}).get("home", {}).get("hits")
            away_errors = linescore.get("teams", {}).get("away", {}).get("errors")
            home_errors = linescore.get("teams", {}).get("home", {}).get("errors")

            # Get decisions data for winning pitcher
            winning_pitcher = decisions.get("winner", {}).get("fullName")

            # Determine top performer based on game stats
            top_performer = None
            max_hits = 0
            max_rbi = 0

            # Process both teams' batting stats
            for team_data in boxscore.get("teams", {}).values():
                for player_id, player in team_data.get("players", {}).items():
                    batting_stats = player.get("stats", {}).get("batting", {})
                    hits = batting_stats.get("hits", 0)
                    rbi = batting_stats.get("rbi", 0)

                    # Update top performer based on hits and RBIs
                    if hits > max_hits or (hits == max_hits and rbi > max_rbi):
                        max_hits = hits
                        max_rbi = rbi
                        top_performer = player.get("person", {}).get("fullName")

            # Process game events
            events = []
            for play in plays.get("allPlays", []):
                if play.get("about", {}).get("isComplete", False) and (
                    play.get("result", {}).get("rbi", 0) > 0
                    or play.get("result", {}).get("event")
                    in ["Home Run", "Triple", "Double"]
                ):
                    events.append(
                        {
                            "inning": str(play.get("about", {}).get("inning")),
                            "title": play.get("result", {}).get("event"),
                            "description": play.get("result", {}).get(
                                "description", ""
                            ),
                        }
                    )

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
                away_hits=away_hits,
                home_hits=home_hits,
                away_errors=away_errors,
                home_errors=home_errors,
                winning_pitcher=winning_pitcher,
                top_performer=top_performer,
                events=events,
            )
        except KeyError:
            return None

    async def get_game_details(self, game_id: int) -> Optional[dict]:
        """Fetch detailed game data from MLB GUMBO API."""
        url = f"{self.gumbo_url}/game/{game_id}/feed/live"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    response.raise_for_status()
                    return await response.json()
        except (aiohttp.ClientError, ValueError, asyncio.TimeoutError):
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
