from collections.abc import AsyncIterator

from redis.asyncio import Redis

from app.config import get_settings


async def get_redis() -> AsyncIterator[Redis | None]:
    redis_url = get_settings().redis_url
    if not redis_url:
        yield None
        return

    client = Redis.from_url(redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()
