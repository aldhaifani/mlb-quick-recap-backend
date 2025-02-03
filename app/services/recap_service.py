from typing import Optional, Dict
from datetime import datetime
import google.generativeai as genai
from app.config import settings
from app.models.game import Game


class RecapService:
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-pro")

    async def generate_recap(
        self, game: Game, game_stats: dict, target_language: str = "en"
    ) -> Optional[str]:
        """Generate a natural language recap of the game using Google's Gemini AI model."""
        try:
            # Prepare the game data for the prompt
            prompt = self._create_recap_prompt(game, game_stats)

            # Generate the recap using Gemini
            response = await self.model.generate_content_async(prompt)

            if not response.text:
                return None

            recap = response.text.strip()

            # If target language is not English, translate the recap
            if target_language != "en":
                translated_recap = await self._translate_recap(recap, target_language)
                return translated_recap

            return recap

        except Exception as e:
            print(f"Error generating recap: {str(e)}")
            return None

    def _create_recap_prompt(self, game: Game, game_stats: dict) -> str:
        """Create a structured prompt for the AI model to generate the game recap."""
        # Extract relevant information
        home_team = game.teams["home"].name
        away_team = game.teams["away"].name
        home_score = game.score.home
        away_score = game.score.away
        venue = game.venue
        date = game.date.strftime("%B %d, %Y")

        # Get team stats
        team_stats = game_stats.get("team_stats", {})
        key_plays = game_stats.get("key_plays", [])
        decisions = game_stats.get("decisions", {})
        game_info = game_stats.get("game_info", {})

        # Construct the prompt
        prompt = f"""Generate a concise and engaging MLB game recap for the following game:

Game Details:
- Date: {date}
- Venue: {venue}
- Final Score: {away_team} {away_score}, {home_team} {home_score}
- Attendance: {game_info.get("attendance", "N/A")}
- Game Duration: {game_info.get("game_time", "N/A")} minutes

Key Statistics:
{self._format_team_stats(team_stats)}

Key Plays:
{self._format_key_plays(key_plays)}

Game Decisions:
- Winning Pitcher: {decisions.get("winner", "N/A")}
- Losing Pitcher: {decisions.get("loser", "N/A")}
- Save: {decisions.get("save", "N/A")}

Please write a natural, engaging recap that highlights the most important aspects of the game, including key performances, turning points, and notable achievements. Focus on telling a compelling story while maintaining accuracy and including relevant statistics."""

        return prompt

    def _format_team_stats(self, team_stats: dict) -> str:
        """Format team statistics for the prompt."""
        formatted_stats = []
        for team_id, stats in team_stats.items():
            batting = stats["batting"]
            pitching = stats["pitching"]

            # Add team batting stats
            formatted_stats.append(f"Team {team_id} Batting:")
            formatted_stats.append(f"- Hits: {batting['hits']}")
            formatted_stats.append(f"- Runs: {batting['runs']}")
            formatted_stats.append(f"- Strikeouts: {batting['strikeouts']}")
            formatted_stats.append(f"- Walks: {batting['walks']}")

            # Add notable batting performances
            for highlight in batting["batting_highlights"]:
                if highlight["hits"] > 0:
                    formatted_stats.append(
                        f"- {highlight['player_name']}: {highlight['hits']} H, "
                        f"{highlight['home_runs']} HR, {highlight['rbi']} RBI"
                    )

            # Add team pitching stats
            formatted_stats.append(f"\nTeam {team_id} Pitching:")
            for highlight in pitching["pitching_highlights"]:
                formatted_stats.append(
                    f"- {highlight['player_name']}: {highlight['innings_pitched']} IP, "
                    f"{highlight['strikeouts']} K, {highlight['earned_runs']} ER"
                )

        return "\n".join(formatted_stats)

    def _format_key_plays(self, key_plays: list) -> str:
        """Format key plays for the prompt."""
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
        """Translate the game recap to the target language using Google Cloud Translate."""
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
