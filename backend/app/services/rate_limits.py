from dataclasses import dataclass
from typing import Protocol

from redis.exceptions import RedisError

from app.errors import ApiError


class RedisLike(Protocol):
    async def incr(self, key: str) -> int: ...

    async def expire(self, key: str, seconds: int) -> object: ...

    async def ttl(self, key: str) -> int: ...


@dataclass(frozen=True, slots=True)
class RateLimit:
    max_requests: int
    window_seconds: int


async def check_rate_limit(redis: RedisLike | None, key: str, limit: RateLimit) -> None:
    if redis is None:
        return

    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, limit.window_seconds)
        if count > limit.max_requests:
            retry_after = await redis.ttl(key)
            raise ApiError(
                status_code=429,
                code="rate_limited",
                message="Too many requests. Please try again later.",
                detail={"retry_after_seconds": max(retry_after, 1)},
            )
    except RedisError:
        return
