"""Async Riot API client with rate limiting and caching."""

import asyncio
import logging

import httpx

from oraclegg.config import settings
from oraclegg.riot.rate_limiter import RiotRateLimiter
from oraclegg.riot.types import (
    AccountDTO,
    ChampionMasteryDTO,
    LeagueEntryDTO,
    MatchDTO,
    SummonerDTO,
)

logger = logging.getLogger(__name__)


class RiotAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Riot API {status_code}: {message}")


class RiotClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.riot_api_key
        self.rate_limiter = RiotRateLimiter()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={"X-Riot-Token": self.api_key},
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(self, url: str, retries: int = 3) -> dict | list:
        """Make a rate-limited request with retry logic."""
        await self.rate_limiter.acquire()
        client = await self._get_client()

        for attempt in range(retries):
            try:
                resp = await client.get(url)

                # Parse rate limit headers to stay in sync
                self._parse_rate_headers(resp.headers)

                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                elif resp.status_code == 404:
                    raise RiotAPIError(404, f"Not found: {url}")
                elif resp.status_code >= 500:
                    wait = 2 ** attempt
                    logger.warning(f"Server error {resp.status_code}, retrying in {wait}s")
                    await asyncio.sleep(wait)
                    continue
                else:
                    raise RiotAPIError(resp.status_code, resp.text)
            except httpx.RequestError as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise RiotAPIError(0, str(e))

        raise RiotAPIError(429, "Exhausted retries")

    def _parse_rate_headers(self, headers: httpx.Headers):
        """Update rate limiter from Riot's response headers."""
        app_limit = headers.get("X-App-Rate-Limit")
        if app_limit:
            try:
                parts = app_limit.split(",")
                for part in parts:
                    count, seconds = part.split(":")
                    if int(seconds) <= 2:
                        per_sec = int(count)
                    else:
                        per_long = int(count)
                self.rate_limiter.update_limits(per_sec, per_long)
            except (ValueError, UnboundLocalError):
                pass

    # ─── Account-V1 ──────────────────────────────────────────────────────

    async def get_account_by_riot_id(self, game_name: str, tag_line: str) -> AccountDTO:
        url = f"{settings.riot_base_url}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        data = await self._request(url)
        return AccountDTO(**data)

    async def get_account_by_puuid(self, puuid: str) -> AccountDTO:
        url = f"{settings.riot_base_url}/riot/account/v1/accounts/by-puuid/{puuid}"
        data = await self._request(url)
        return AccountDTO(**data)

    # ─── Summoner-V4 ─────────────────────────────────────────────────────

    async def get_summoner_by_puuid(self, puuid: str) -> SummonerDTO:
        url = f"{settings.platform_base_url}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        data = await self._request(url)
        return SummonerDTO(**data)

    # ─── League-V4 ───────────────────────────────────────────────────────

    async def get_league_entries(self, summoner_id: str) -> list[LeagueEntryDTO]:
        url = f"{settings.platform_base_url}/lol/league/v4/entries/by-summoner/{summoner_id}"
        data = await self._request(url)
        return [LeagueEntryDTO(**entry) for entry in data]

    # ─── Champion-Mastery-V4 ─────────────────────────────────────────────

    async def get_champion_mastery(
        self, puuid: str, top: int = 10
    ) -> list[ChampionMasteryDTO]:
        url = f"{settings.platform_base_url}/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count={top}"
        data = await self._request(url)
        return [ChampionMasteryDTO(**m) for m in data]

    # ─── Match-V5 ────────────────────────────────────────────────────────

    async def get_match_ids(
        self,
        puuid: str,
        queue: int | None = 420,  # 420 = ranked solo
        count: int = 10,
        start: int = 0,
    ) -> list[str]:
        params = f"?count={count}&start={start}"
        if queue is not None:
            params += f"&queue={queue}"
        url = f"{settings.riot_base_url}/lol/match/v5/matches/by-puuid/{puuid}/ids{params}"
        return await self._request(url)

    async def get_match(self, match_id: str) -> MatchDTO:
        url = f"{settings.riot_base_url}/lol/match/v5/matches/{match_id}"
        data = await self._request(url)
        return MatchDTO(**data)

    async def get_match_timeline(self, match_id: str) -> dict:
        url = f"{settings.riot_base_url}/lol/match/v5/matches/{match_id}/timeline"
        return await self._request(url)

    # ─── League-Exp-V4 (for pipeline) ───────────────────────────────────

    async def get_league_exp_entries(
        self, queue: str = "RANKED_SOLO_5x5", tier: str = "MASTER", division: str = "I",
        page: int = 1, platform: str | None = None,
    ) -> list[dict]:
        base = f"https://{platform or settings.riot_platform}.api.riotgames.com"
        url = f"{base}/lol/league-exp/v4/entries/{queue}/{tier}/{division}?page={page}"
        return await self._request(url)
