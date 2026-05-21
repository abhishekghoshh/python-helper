import redis.asyncio as aioredis
from fastapi_todo_service.core.config import settings

class RedisClient:
    def __init__(self):
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def get(self, key: str) -> str | None:
        return await self.redis.get(key)

    async def set(self, key: str, value: str, ex: int = 3600) -> None:
        await self.redis.set(key, value, ex=ex)

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)

redis_client = RedisClient()

async def get_redis():
    return redis_client