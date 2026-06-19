"""Redis Client for Caching and Streams"""

import json
from typing import Optional
import redis.asyncio as redis
from app.core.config import settings


class RedisClient:
    def __init__(self):
        self._client: Optional[redis.Redis] = None

    async def connect(self):
        self._client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def disconnect(self):
        if self._client:
            await self._client.close()

    async def get(self, key: str) -> Optional[str]:
        return await self._client.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None):
        await self._client.set(key, value, ex=ex)

    async def delete(self, key: str):
        await self._client.delete(key)

    async def publish(self, channel: str, message: dict):
        await self._client.publish(channel, json.dumps(message))

    async def xadd(self, stream: str, data: dict) -> str:
        return await self._client.xadd(stream, data)

    async def xread(self, streams: dict, count: Optional[int] = None):
        return await self._client.xread(streams, count=count)

    async def sadd(self, key: str, *values):
        await self._client.sadd(key, *values)

    async def sismember(self, key: str, value) -> bool:
        return await self._client.sismember(key, value)


redis_client = RedisClient()
