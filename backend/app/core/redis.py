"""Redis Client for Caching, Streams, and Pub/Sub"""

import json
from typing import Optional, Union, List, Dict, Any
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

    # ============== Basic Key-Value ==============
    async def get(self, key: str) -> Optional[str]:
        return await self._client.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None):
        await self._client.set(key, value, ex=ex)

    async def delete(self, key: str):
        await self._client.delete(key)

    async def expire(self, key: str, seconds: int):
        await self._client.expire(key, seconds)

    # ============== Pub/Sub ==============
    async def publish(self, channel: str, message: str):
        await self._client.publish(channel, message)

    def pubsub(self):
        return self._client.pubsub()

    # ============== Streams ==============
    async def xadd(self, stream: str, fields: dict, maxlen: Optional[int] = None) -> str:
        """Add entry to stream"""
        return await self._client.xadd(stream, fields, maxlen=maxlen)

    async def xread(self, streams: dict, count: Optional[int] = None, block: Optional[int] = None) -> List:
        """Read from streams"""
        return await self._client.xread(streams, count=count, block=block)

    async def xrange(self, stream: str, min: str = '-', max: str = '+', count: Optional[int] = None) -> List:
        """Read range from stream"""
        return await self._client.xrange(stream, min=min, max=max, count=count)

    async def xlen(self, stream: str) -> int:
        """Get stream length"""
        return await self._client.xlen(stream)

    # ============== Consumer Groups ==============
    async def xgroup_create(self, stream: str, group: str, id: str = '0', mkstream: bool = True):
        """Create consumer group"""
        try:
            await self._client.xgroup_create(stream, group, id=id, mkstream=mkstream)
        except redis.ResponseError as e:
            if 'BUSYGROUP' not in str(e):
                raise

    async def xgroup_destroy(self, stream: str, group: str):
        """Destroy consumer group"""
        await self._client.xgroup_destroy(stream, group)

    async def xreadgroup(
        self,
        group: str,
        consumer: str,
        streams: dict,
        count: Optional[int] = None,
        block: Optional[int] = None,
        noack: bool = False
    ) -> List:
        """Read from stream as consumer group member"""
        return await self._client.xreadgroup(
            group,
            consumer,
            streams,
            count=count,
            block=block,
            noack=noack
        )

    async def xack(self, stream: str, group: str, *ids):
        """Acknowledge message processing"""
        if ids:
            return await self._client.xack(stream, group, *ids)
        return 0

    async def xpending(self, stream: str, group: str, min: str = '-', max: str = '+', count: int = 10) -> List:
        """Get pending messages info"""
        return await self._client.xpending_range(stream, group, min=min, max=max, count=count)

    async def xclaim(
        self,
        stream: str,
        group: str,
        consumer: str,
        min_idle_time: int,
        message_ids: List[str]
    ) -> List:
        """Claim pending messages"""
        if not message_ids:
            return []
        return await self._client.xclaim(stream, group, consumer, min_idle_time, message_ids)

    # ============== Sets ==============
    async def sadd(self, key: str, *values):
        await self._client.sadd(key, *values)

    async def sismember(self, key: str, value) -> bool:
        return await self._client.sismember(key, value)


redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Get Redis client instance"""
    return redis_client
