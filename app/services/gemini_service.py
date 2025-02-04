import google.generativeai as genai
from app.models.game import GameList
from app.config import settings
import json
import asyncio

genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)


class GeminiService:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-1.5-flash-8b")
        self.generation_config = {
            "temperature": 0.1,
            "top_p": 0.8,
            "max_output_tokens": 8192,
            "candidate_count": 1,
        }

    def _generate_prompt(self, games: GameList) -> str:
        prompt = """You are a specialized MLB game summarizer. Your task is to create concise game summaries in a strict JSON format.

Game Data:r
{}

Instructions:
1. Create a JSON object with game IDs as keys and language-specific summaries as values
2. For each game, provide summaries in three languages (en, es, ja):
   - English (en): Original summary
   - Spanish (es): Spanish translation
   - Japanese (ja): Japanese translation
3. Each summary should be 2-3 sentences highlighting:
   - Final score and winning team
   - Key performances (top performer, winning pitcher)
   - Notable plays from events list
4. Use specific stats (hits, errors) to add context
5. Return ONLY the JSON object, no additional text

Format:
{{
    "<game_id>": {{
        "en": "English summary",
        "es": "Spanish summary",
        "ja": "Japanese summary"
    }}
}}""".format(json.dumps(games.model_dump(), indent=2, default=str))
        return prompt

    async def _process_game_batch(self, games_batch: list) -> dict:
        """Process a batch of games and generate summaries."""
        batch_games = GameList(total_items=len(games_batch), games=games_batch)
        prompt = self._generate_prompt(batch_games)

        try:
            response = await self.model.generate_content_async(
                prompt, generation_config=self.generation_config
            )

            if response.text:
                cleaned_text = response.text.strip()
                cleaned_text = (
                    cleaned_text.replace("```json", "").replace("```", "").strip()
                )

                if cleaned_text.startswith("{") and cleaned_text.endswith("}"):
                    try:
                        return json.loads(cleaned_text)
                    except json.JSONDecodeError:
                        pass

        except Exception as e:
            print(f"Error processing game batch: {e}")

        return {}

    async def set_game_summary(self, games: GameList) -> GameList:
        """Process all games in parallel batches and set their summaries."""
        BATCH_SIZE = 3  # Maximum number of games per batch for token limit

        # Split games into batches
        game_batches = [
            games.games[i : i + BATCH_SIZE]
            for i in range(0, len(games.games), BATCH_SIZE)
        ]

        # Process batches concurrently
        batch_results = await asyncio.gather(
            *[self._process_game_batch(batch) for batch in game_batches]
        )

        # Combine results and update game summaries
        all_summaries = {}
        for batch_summary in batch_results:
            all_summaries.update(batch_summary)

        # Update game summaries with results
        for game in games.games:
            game_id = str(game.id)
            if game_id in all_summaries:
                game.summary = {
                    "en": all_summaries[game_id].get(
                        "en", "No English summary available."
                    ),
                    "es": all_summaries[game_id].get(
                        "es", "No Spanish summary available."
                    ),
                    "ja": all_summaries[game_id].get(
                        "ja", "No Japanese summary available."
                    ),
                }
            else:
                self._set_default_summary(game)

        return games

    def _set_default_summary(self, game):
        game.summary = {
            "en": f"{game.teams['away'].name} vs {game.teams['home'].name} - Final score: {game.score.away}-{game.score.home}",
            "es": f"{game.teams['away'].name} vs {game.teams['home'].name} - Resultado final: {game.score.away}-{game.score.home}",
            "ja": f"{game.teams['away'].name} vs {game.teams['home'].name} - 最終スコア: {game.score.away}-{game.score.home}",
        }
