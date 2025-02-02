# app/services/translation_service.py
from google.cloud import translate
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class TranslationService:
    def __init__(self):
        self.client = translate.TranslationServiceClient()
        self.supported_languages = {"es": "Spanish", "ja": "Japanese"}

    async def translate_recap(self, text: str, project_id: str) -> Dict[str, str]:
        """
        Translates the game recap to supported languages
        Returns dict with language codes as keys and translations as values
        """
        translations = {"en": text}
        parent = f"projects/{project_id}/locations/global"

        for target_language in self.supported_languages:
            try:
                response = self.client.translate_text(
                    request={
                        "parent": parent,
                        "contents": [text],
                        "mime_type": "text/plain",
                        "source_language_code": "en",
                        "target_language_code": target_language,
                    }
                )

                translations[target_language] = response.translations[0].translated_text
                logger.info(
                    f"Successfully translated to {self.supported_languages[target_language]}"
                )

            except Exception as e:
                logger.error(f"Translation failed for {target_language}: {str(e)}")
                translations[target_language] = (
                    text  # Fallback to English if translation fails
                )

        return translations
