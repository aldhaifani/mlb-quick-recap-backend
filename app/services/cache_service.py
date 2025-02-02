import json
from typing import Any, Optional
import redis
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisCache:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )

    async def get(self, key: str) -> Optional[Any]:
        try:
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Redis get error: {str(e)}")
            return None

    async def set(self, key: str, value: Any, expire: int = 600) -> bool:
        try:
            return self.redis_client.setex(key, expire, json.dumps(value))
        except Exception as e:
            logger.error(f"Redis set error: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Redis delete error: {str(e)}")
            return False

    def generate_key(self, *args: Any) -> str:
        return ":".join(str(arg) for arg in args)
