"""Tests for dual token bucket rate limiter."""

import asyncio
import time

import pytest

from oraclegg.riot.rate_limiter import RiotRateLimiter, TokenBucket


class TestTokenBucket:
    async def test_initial_tokens_equal_rate(self):
        bucket = TokenBucket(rate=5, period=1.0)
        assert bucket.tokens == 5

    async def test_acquire_decrements_token(self):
        bucket = TokenBucket(rate=5, period=1.0)
        await bucket.acquire()
        # tokens should be approximately 4 (some tiny refill may have happened)
        assert bucket.tokens < 5

    async def test_deplete_all_tokens(self):
        bucket = TokenBucket(rate=3, period=1.0)
        for _ in range(3):
            await bucket.acquire()
        # After 3 acquires on a rate-3 bucket, tokens should be near 0
        assert bucket.tokens < 1

    async def test_refill_adds_tokens(self):
        bucket = TokenBucket(rate=10, period=1.0)
        # Drain all tokens
        for _ in range(10):
            await bucket.acquire()
        assert bucket.tokens < 1

        # Simulate time passing by backdating last_refill
        bucket.last_refill = time.monotonic() - 0.5  # half period elapsed
        bucket._refill()
        # Should have refilled ~5 tokens (10 rate / 1.0 period * 0.5 elapsed)
        assert bucket.tokens >= 4  # allow small floating point drift

    async def test_refill_caps_at_rate(self):
        bucket = TokenBucket(rate=5, period=1.0)
        # Backdate heavily — even after long time, tokens should not exceed rate
        bucket.last_refill = time.monotonic() - 100
        bucket._refill()
        assert bucket.tokens == 5

    async def test_concurrent_acquire_respects_lock(self):
        bucket = TokenBucket(rate=5, period=1.0)
        # Fire 5 concurrent acquires — all should complete without error
        await asyncio.gather(*(bucket.acquire() for _ in range(5)))
        # Tokens should be near 0
        assert bucket.tokens < 1

    async def test_zero_rate_bucket(self):
        """Edge case: rate=0 should not crash."""
        bucket = TokenBucket(rate=0, period=1.0)
        assert bucket.tokens == 0


class TestRiotRateLimiter:
    async def test_default_limits(self):
        rl = RiotRateLimiter()
        assert rl.short.rate == 20
        assert rl.long.rate == 100

    async def test_custom_limits(self):
        rl = RiotRateLimiter(per_second=10, per_two_minutes=50)
        assert rl.short.rate == 10
        assert rl.long.rate == 50

    async def test_acquire_depletes_both_buckets(self):
        rl = RiotRateLimiter(per_second=5, per_two_minutes=100)
        await rl.acquire()
        assert rl.short.tokens < 5
        assert rl.long.tokens < 100

    async def test_update_limits_replaces_bucket(self):
        rl = RiotRateLimiter(per_second=20, per_two_minutes=100)
        rl.update_limits(per_second=10, per_two_minutes=50)
        assert rl.short.rate == 10
        assert rl.long.rate == 50
        # New bucket should be full
        assert rl.short.tokens == 10

    async def test_update_limits_no_change_keeps_bucket(self):
        rl = RiotRateLimiter(per_second=20, per_two_minutes=100)
        await rl.acquire()
        old_short = rl.short
        old_long = rl.long
        rl.update_limits(per_second=20, per_two_minutes=100)
        assert rl.short is old_short
        assert rl.long is old_long

    async def test_concurrent_riot_acquire(self):
        rl = RiotRateLimiter(per_second=10, per_two_minutes=100)
        await asyncio.gather(*(rl.acquire() for _ in range(10)))
        assert rl.short.tokens < 1
