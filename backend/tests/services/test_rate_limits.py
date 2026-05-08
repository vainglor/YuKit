import pytest

from app.errors import ApiError
from app.services.rate_limits import RateLimit, check_rate_limit


class FakeRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds

    async def ttl(self, key: str) -> int:
        return self.expirations.get(key, 60)


@pytest.mark.asyncio
async def test_check_rate_limit_allows_until_limit() -> None:
    redis = FakeRedis()
    limit = RateLimit(max_requests=2, window_seconds=60)

    await check_rate_limit(redis, "rate:test", limit)
    await check_rate_limit(redis, "rate:test", limit)

    assert redis.counts["rate:test"] == 2


@pytest.mark.asyncio
async def test_check_rate_limit_raises_after_limit() -> None:
    redis = FakeRedis()
    limit = RateLimit(max_requests=1, window_seconds=60)

    await check_rate_limit(redis, "rate:test", limit)

    with pytest.raises(ApiError) as exc_info:
        await check_rate_limit(redis, "rate:test", limit)

    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "rate_limited"
