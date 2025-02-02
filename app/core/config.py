from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from datetime import datetime


class Settings(BaseSettings):
    # API Configuration
    API_VERSION: str
    DEBUG: bool
    ENVIRONMENT: str

    # Redis Configuration
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str | None = None

    # Google Cloud Configuration
    GOOGLE_CLOUD_PROJECT: str
    GOOGLE_APPLICATION_CREDENTIALS: str

    # MLB API Configuration
    MLB_API_BASE_URL: str
    MLB_GUMBO_API_BASE_URL: str
    MLB_DATA_START_YEAR: int = 2008

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def current_year(self) -> int:
        return datetime.now().year

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
