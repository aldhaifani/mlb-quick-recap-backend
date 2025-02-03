from pydantic_settings import BaseSettings
from typing import Optional


from enum import Enum


class MLBGameType(str, Enum):
    REGULAR = "R"
    POSTSEASON = "P"
    SPRING = "S"


class Settings(BaseSettings):
    # API Configuration
    API_VERSION: str = "v1"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # MLB API Configuration
    MLB_API_BASE_URL: str = "https://statsapi.mlb.com/api/v1"
    MLB_GUMBO_API_BASE_URL: str = "https://statsapi.mlb.com/api/v1.1"
    MLB_DATA_START_YEAR: int = 2008
    MLB_SPORT_ID: int = 1  # MLB = 1

    # Google Cloud Configuration
    GOOGLE_CLOUD_PROJECT: str
    GOOGLE_CREDENTIALS_JSON: str
    GOOGLE_GEMINI_API_KEY: str
    GOOGLE_TRANSLATE_API_KEY: str

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_SSL: bool = False

    # Cache Configuration
    CACHE_TTL: int = 600  # 10 minutes in seconds

    class Config:
        env_file = ".env"


settings = Settings()
