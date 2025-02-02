from typing import Dict, List
import google.generativeai as genai
from app.core.config import get_settings
import logging
from enum import Enum
from time import sleep

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiModel(str, Enum):
    PRIMARY = "gemini-1.5-pro"
    FLASH = "gemini-1.5-flash"
    FLASH_8B = "gemini-1.5-flash-8b"


class AIService:
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.models = {
            GeminiModel.PRIMARY: {
                "model": genai.GenerativeModel(GeminiModel.PRIMARY),
                "config": {
                    "temperature": 0.7,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 256,
                },
            },
            GeminiModel.FLASH: {
                "model": genai.GenerativeModel(GeminiModel.FLASH),
                "config": {
                    "temperature": 0.7,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 256,
                },
            },
            GeminiModel.FLASH_8B: {
                "model": genai.GenerativeModel(GeminiModel.FLASH_8B),
                "config": {
                    "temperature": 0.7,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 256,
                },
            },
        }
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    async def generate_game_recap(self, game_data: Dict) -> str:
        prompt = self._create_recap_prompt(game_data)

        # Try models in order of preference
        for model_name in GeminiModel:
            for attempt in range(self.max_retries):
                try:
                    model_config = self.models[model_name]
                    response = model_config["model"].generate_content(
                        prompt, generation_config=model_config["config"]
                    )
                    logger.info(f"Successfully generated recap using {model_name}")
                    return self._process_recap_response(response.text)
                except Exception as e:
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {model_name}: {str(e)}"
                    )
                    if attempt < self.max_retries - 1:
                        sleep(self.retry_delay)
                    continue

            logger.warning(f"All attempts failed for {model_name}, trying next model")

        # If all models fail, use fallback
        logger.error("All models failed to generate recap, using fallback")
        return self._generate_fallback_recap(game_data)

    def _create_recap_prompt(self, game_data: Dict) -> str:
        return f"""
        Create a concise baseball game recap for the following game:
        
        {game_data["awayTeam"]} vs {game_data["homeTeam"]}
        Final Score: {game_data["awayScore"]} - {game_data["homeScore"]}
        
        Key Statistics:
        - Hits: {game_data["awayHits"]}-{game_data["homeHits"]}
        - Errors: {game_data["awayErrors"]}-{game_data["homeErrors"]}
        
        Important plays and events:
        {self._format_plays(game_data["plays"])}
        
        Generate a natural, engaging recap in 2-3 sentences that captures the key moments 
        and the flow of the game. Focus on the most impactful plays and players.
        """

    def _format_plays(self, plays: List[Dict]) -> str:
        important_plays = []
        for play in plays:
            if play.get("about", {}).get("isComplete", False) and (
                play.get("result", {}).get("rbi", 0) > 0
                or play.get("result", {}).get("event")
                in ["Home Run", "Triple", "Double", "Error"]
            ):
                important_plays.append(
                    f"- {play['about']['inning']} inning: {play['result']['description']}"
                )
        return "\n".join(important_plays)

    def _process_recap_response(self, response: str) -> str:
        return response.strip().replace("\n\n", " ").replace("  ", " ")

    def _generate_fallback_recap(self, game_data: Dict) -> str:
        winner = (
            game_data["homeTeam"]
            if game_data["homeScore"] > game_data["awayScore"]
            else game_data["awayTeam"]
        )
        loser = (
            game_data["awayTeam"]
            if winner == game_data["homeTeam"]
            else game_data["homeTeam"]
        )
        winner_score = max(game_data["homeScore"], game_data["awayScore"])
        loser_score = min(game_data["homeScore"], game_data["awayScore"])

        return f"{winner} defeated {loser} {winner_score}-{loser_score} in a game at {game_data.get('venue', 'their home field')}."
