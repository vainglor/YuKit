from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import get_settings


def redis_settings_from_url(url: str) -> RedisSettings:
    return RedisSettings.from_dsn(url)


async def get_arq_pool() -> ArqRedis | None:
    redis_url = get_settings().redis_url
    if not redis_url:
        return None
    return await create_pool(redis_settings_from_url(redis_url))
