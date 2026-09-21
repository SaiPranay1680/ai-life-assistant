from __future__ import annotations

import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from ..core.config import settings

logger = logging.getLogger(__name__)

_client: Redis | None = None


def _redis() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def allow_request(key: str, *, limit: int, window_seconds: int) -> bool:
    try:
        client = _redis()
        current = await client.incr(key)
        if current == 1:
            await client.expire(key, window_seconds)
        return int(current) <= limit
    except RedisError:
        logger.warning("Rate limiter unavailable")
        return False


async def cooldown_remaining(key: str) -> int:
    try:
        ttl = await _redis().ttl(key)
        return max(int(ttl or 0), 0)
    except RedisError:
        return 0


async def set_cooldown(key: str, seconds: int) -> None:
    try:
        await _redis().set(key, "1", ex=seconds)
    except RedisError:
        logger.warning("Rate limiter unavailable")


async def consume_once(key: str, *, ttl_seconds: int) -> bool:
    try:
        created = await _redis().set(key, "1", ex=ttl_seconds, nx=True)
        return bool(created)
    except RedisError:
        logger.warning("Rate limiter unavailable")
        return False
