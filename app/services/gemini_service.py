import google.generativeai as genai
from app.models.game import GameList
from app.config import settings
from app.cache.redis_manager import RedisManager
import json
import asyncio

genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)


class GeminiService:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-pro")
        self.generation_config = {
            "temperature": 0.3,
            "top_p": 0.9,
            "max_output_tokens": 2048,
            "candidate_count": 1,
        }
        self.redis_manager = RedisManager()

    def _generate_prompt(self, games: GameList) -> str:
        prompt = """You are a specialized MLB game summarizer. Your task is to create concise game summaries in a strict JSON format.

Game Data:
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

            if not response.parts:
                return {}

            try:
                cleaned_text = response.text.strip()
                # Remove any markdown code block markers
                cleaned_text = (
                    cleaned_text.replace("```json", "").replace("```", "").strip()
                )

                # Ensure we have valid JSON
                if cleaned_text.startswith("{") and cleaned_text.endswith("}"):
                    return json.loads(cleaned_text)
            except (AttributeError, json.JSONDecodeError) as e:
                print(f"Error parsing response: {e}")
                return {}

        except Exception as e:
            print(f"Error processing game batch: {e}")

        return {}

    async def set_game_summary(self, games: GameList) -> GameList:
        """Process all games in parallel batches and set their summaries with caching."""
        BATCH_SIZE = 5  # Increased batch size for better throughput

        # Check cache for each game first
        uncached_games = []
        for game in games.games:
            game_id = str(game.id)
            cached_summary = await self.redis_manager.get_games(
                game.date.year, game.teams["home"].id
            )
            if cached_summary and game_id in cached_summary.games:
                game.summary = cached_summary.games[game_id].summary
            else:
                uncached_games.append(game)

        if not uncached_games:
            return games

        # Process uncached games in parallel batches
        game_batches = [
            uncached_games[i : i + BATCH_SIZE]
            for i in range(0, len(uncached_games), BATCH_SIZE)
        ]

        # Process batches concurrently with semaphore to control API rate
        semaphore = asyncio.Semaphore(3)  # Limit concurrent API calls

        async def process_batch_with_semaphore(batch):
            async with semaphore:
                return await self._process_game_batch(batch)

        batch_results = await asyncio.gather(
            *[process_batch_with_semaphore(batch) for batch in game_batches]
        )

        # Combine results and update game summaries
        all_summaries = {}
        for batch_summary in batch_results:
            all_summaries.update(batch_summary)

        # Update game summaries and cache results
        for game in uncached_games:
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
                # Cache the game summary
                await self.redis_manager.set_games(
                    GameList(total_items=1, games=[game]),
                    game.date.year,
                    game.teams["home"].id,
                )
            else:
                self._set_default_summary(game)

        return games

    def _set_default_summary(self, game):
        game.summary = {
            "en": f"{game.teams['away'].name} vs {game.teams['home'].name} - Final score: {game.score.away}-{game.score.home}",
            "es": f"{game.teams['away'].name} vs {game.teams['home'].name} - Resultado final: {game.score.away}-{game.score.home}",
            "ja": f"{game.teams['away'].name} vs {game.teams['home'].name} - 最終スコア: {game.score.away}-{game.score.home}",
        }
