from typing import Optional
import google.generativeai as genai
from app.config import settings
from app.models.game import Game
import asyncio
import time
from collections import deque
from collections import deque


class RecapService:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-pro")
        self.generation_config = {
            "temperature": 0.3,
            "top_p": 0.9,
            "max_output_tokens": 512,
            "candidate_count": 1,
        }
        self._request_timestamps = deque(maxlen=60)
        self._rate_limit = 60
        self._time_window = 60

    def _check_rate_limit(self) -> bool:
        current_time = time.time()
        # Clean up old timestamps
        while (
            self._request_timestamps
            and current_time - self._request_timestamps[0] > self._time_window
        ):
            self._request_timestamps.popleft()
        return len(self._request_timestamps) < self._rate_limit

    async def _wait_for_rate_limit(self):
        while not self._check_rate_limit():
            await asyncio.sleep(1)  # Wait for 1 second before checking again
        self._request_timestamps.append(time.time())

    async def generate_recap(
        self, game: Game, game_stats: dict, target_language: str = "en"
    ) -> Optional[str]:
        prompt = self._create_recap_prompt(game, game_stats)

        try:
            await self._wait_for_rate_limit()
            response = await self.model.generate_content_async(
                prompt,
                generation_config=self.generation_config,
            )

            if not response.text:
                return self._generate_fallback_recap(game)

            recap = response.text.strip()
            if target_language != "en":
                return await self._translate_recap(recap, target_language)
            return recap

        except Exception as e:
            print(f"Error generating recap: {e}")
            return self._generate_fallback_recap(game)

    def _create_recap_prompt(self, game: Game, game_stats: dict) -> str:
        home_team = game.teams["home"].name
        away_team = game.teams["away"].name
        winner = "home" if game.score.home > game.score.away else "away"
        winner_team = game.teams[winner].name
        winner_score = game.score.home if winner == "home" else game.score.away
        loser_team = game.teams["away" if winner == "home" else "home"].name
        loser_score = game.score.away if winner == "home" else game.score.home

        team_stats = game_stats.get("team_stats", {})
        key_plays = game_stats.get("key_plays", [])
        decisions = game_stats.get("decisions", {})

        prompt = f"""MLB Game Recap:
{winner_team} defeated {loser_team} {winner_score}-{loser_score}

Key Stats:
{self._format_team_stats(team_stats)}

Winning Pitcher: {decisions.get("winner", "N/A")}

Highlights:
{self._format_key_plays(key_plays)}

Provide a concise 2-3 sentence recap focusing on the final score and key performances."""

        return prompt

    def _format_team_stats(self, team_stats: dict) -> str:
        formatted_stats = []
        for team_id, stats in team_stats.items():
            batting = stats["batting"]
            pitching = stats["pitching"]

            formatted_stats.append(f"Team {team_id} Batting:")
            formatted_stats.append(f"- Hits: {batting['hits']}")
            formatted_stats.append(f"- Runs: {batting['runs']}")
            formatted_stats.append(f"- Strikeouts: {batting['strikeouts']}")
            formatted_stats.append(f"- Walks: {batting['walks']}")

            for highlight in batting["batting_highlights"]:
                if highlight["hits"] > 0:
                    formatted_stats.append(
                        f"- {highlight['player_name']}: {highlight['hits']} H, "
                        f"{highlight['home_runs']} HR, {highlight['rbi']} RBI"
                    )

            formatted_stats.append(f"\nTeam {team_id} Pitching:")
            for highlight in pitching["pitching_highlights"]:
                formatted_stats.append(
                    f"- {highlight['player_name']}: {highlight['innings_pitched']} IP, "
                    f"{highlight['strikeouts']} K, {highlight['earned_runs']} ER"
                )

        return "\n".join(formatted_stats)

    def _format_key_plays(self, key_plays: list) -> str:
        formatted_plays = []
        for play in key_plays:
            inning = play["inning"]
            half = play["half_inning"]
            description = play["description"]
            formatted_plays.append(f"- {inning} {half}: {description}")

        return (
            "\n".join(formatted_plays) if formatted_plays else "No key plays recorded"
        )

    async def _translate_recap(self, recap: str, target_language: str) -> Optional[str]:
        try:
            from google.cloud import translate_v2 as translate

            translate_client = translate.Client()
            translation = translate_client.translate(
                recap, target_language=target_language, source_language="en"
            )

            return translation["translatedText"]

        except Exception as e:
            print(f"Error translating recap: {str(e)}")
            return None

    def _generate_fallback_recap(self, game: Game) -> str:
        winner = "home" if game.score.home > game.score.away else "away"
        winner_team = game.teams[winner].name
        winner_score = game.score.home if winner == "home" else game.score.away
        loser_team = game.teams["away" if winner == "home" else "home"].name
        loser_score = game.score.away if winner == "home" else game.score.home

        return f"The {winner_team} defeated the {loser_team} with a score of {winner_score}-{loser_score} at {game.venue}."
