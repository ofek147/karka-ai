import json
import logging
import redis.asyncio as redis
from redis.exceptions import ConnectionError, RedisError
from ..config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


async def get_client() -> redis.Redis:
    global _client
    if not _client:
        _client = redis.from_url(settings.redis_url)
    return _client


async def get_cached(key: str) -> dict | None:
    try:
        r = await get_client()
        val = await r.get(key)
        return json.loads(val) if val else None
    except (ConnectionError, RedisError) as e:
        logger.warning("Redis unavailable, skipping cache read: %s", e)
        return None


async def set_cached(key: str, data: dict, ttl: int | None = None) -> None:
    try:
        r = await get_client()
        await r.setex(key, ttl or settings.cache_ttl_seconds, json.dumps(data, ensure_ascii=False))
    except (ConnectionError, RedisError) as e:
        logger.warning("Redis unavailable, skipping cache write: %s", e)
