"""Redis caching layer with graceful fallback."""

import json
from typing import Any

import redis.asyncio as aioredis
from app.core.config import get_settings
from app.core.logging import logger

_redis: aioredis.Redis | None = None
_memory_cache: dict[str, str] = {}


async def get_redis() -> aioredis.Redis | None:
    global _redis
    if _redis is not None:
        return _redis
    settings = get_settings()
    try:
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await client.ping()
        _redis = client
        return _redis
    except Exception as e:
        logger.warning("redis_unavailable", error=str(e))
        return None


async def cache_get(key: str) -> Any | None:
    client = await get_redis()
    try:
        if client:
            raw = await client.get(key)
            return json.loads(raw) if raw else None
        return json.loads(_memory_cache[key]) if key in _memory_cache else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    settings = get_settings()
    ttl = ttl or settings.cache_ttl
    raw = json.dumps(value, default=str)
    client = await get_redis()
    try:
        if client:
            await client.setex(key, ttl, raw)
        else:
            _memory_cache[key] = raw
    except Exception as e:
        logger.warning("cache_set_failed", key=key, error=str(e))
