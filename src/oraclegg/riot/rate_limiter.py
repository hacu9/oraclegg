import asyncio
import time


class TokenBucket:
    """Simple token bucket rate limiter."""

    def __init__(self, rate: int, period: float):
        self.rate = rate
        self.period = period
        self.tokens = rate
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        new_tokens = elapsed * (self.rate / self.period)
        self.tokens = min(self.rate, self.tokens + new_tokens)
        self.last_refill = now

    async def acquire(self):
        async with self._lock:
            self._refill()
            if self.tokens < 1:
                wait_time = (1 - self.tokens) * (self.period / self.rate)
                await asyncio.sleep(wait_time)
                self._refill()
            self.tokens -= 1


class RiotRateLimiter:
    """Dual token bucket: respects both per-second and per-2-minute Riot limits."""

    def __init__(self, per_second: int = 20, per_two_minutes: int = 100):
        self.short = TokenBucket(per_second, 1.0)
        self.long = TokenBucket(per_two_minutes, 120.0)

    async def acquire(self):
        await self.short.acquire()
        await self.long.acquire()

    def update_limits(self, per_second: int, per_two_minutes: int):
        """Update limits from Riot response headers."""
        if per_second != self.short.rate:
            self.short = TokenBucket(per_second, 1.0)
        if per_two_minutes != self.long.rate:
            self.long = TokenBucket(per_two_minutes, 120.0)
