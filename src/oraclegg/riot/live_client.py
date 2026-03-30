"""Live Client Data API poller.

Polls https://127.0.0.1:2999 during active games for real-time data.
On WSL2, the API runs on Windows side — we try multiple addresses.
"""

import logging
import platform
import subprocess

import httpx

logger = logging.getLogger(__name__)


def _detect_live_client_host() -> str:
    """Detect the correct host for the Live Client Data API.

    On native Windows/macOS: 127.0.0.1
    On WSL2: Windows host IP (from /etc/resolv.conf) since the API binds to Windows localhost.
    """
    # Check if we're in WSL
    try:
        with open("/proc/version", "r") as f:
            if "microsoft" in f.read().lower():
                # WSL2 - get Windows host IP
                with open("/etc/resolv.conf", "r") as rf:
                    for line in rf:
                        if line.startswith("nameserver"):
                            host = line.split()[1]
                            logger.info(f"WSL2 detected, using Windows host: {host}")
                            return host
    except FileNotFoundError:
        pass
    return "127.0.0.1"


LIVE_CLIENT_HOST = _detect_live_client_host()

# On WSL, try bridge first. On native Windows/macOS, go direct.
_is_wsl = False
try:
    with open("/proc/version", "r") as f:
        _is_wsl = "microsoft" in f.read().lower()
except FileNotFoundError:
    pass

if _is_wsl:
    LIVE_CLIENT_BASES = [
        f"http://{LIVE_CLIENT_HOST}:29990",
        "http://172.25.80.1:29990",
        "https://127.0.0.1:2999",
    ]
else:
    LIVE_CLIENT_BASES = [
        "https://127.0.0.1:2999",
    ]


class LiveClientAPI:
    """Polls the League Live Client Data API for in-game data."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._game_active = False
        self._active_base: str | None = None

    @property
    def game_active(self) -> bool:
        return self._game_active

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            # Don't set base_url - we'll try multiple
            self._client = httpx.AsyncClient(
                verify=False,  # Self-signed cert
                timeout=httpx.Timeout(5.0),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._game_active = False

    async def _try_request(self, path: str) -> httpx.Response | None:
        """Try requesting from known base URLs."""
        client = await self._get_client()

        # If we already found a working base, try it first
        if self._active_base:
            try:
                resp = await client.get(f"{self._active_base}{path}")
                if resp.status_code == 200:
                    return resp
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
                self._active_base = None

        # Try all bases
        for base in LIVE_CLIENT_BASES:
            try:
                resp = await client.get(f"{base}{path}")
                if resp.status_code == 200:
                    self._active_base = base
                    return resp
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
                continue
        return None

    async def poll(self) -> dict | None:
        """Fetch all game data. Returns None if game is not running."""
        try:
            resp = await self._try_request("/liveclientdata/allgamedata")
            if resp and resp.status_code == 200:
                if not self._game_active:
                    logger.info(f"Game detected via {self._active_base}")
                self._game_active = True
                return resp.json()
            if self._game_active:
                logger.info("Game ended (Live Client API disconnected)")
            self._game_active = False
            return None
        except Exception:
            if self._game_active:
                logger.info("Game ended (Live Client API disconnected)")
            self._game_active = False
            return None

    async def get_active_player(self) -> dict | None:
        resp = await self._try_request("/liveclientdata/activeplayer")
        return resp.json() if resp else None

    async def get_player_list(self) -> list | None:
        resp = await self._try_request("/liveclientdata/playerlist")
        return resp.json() if resp else None

    async def get_game_stats(self) -> dict | None:
        resp = await self._try_request("/liveclientdata/gamestats")
        return resp.json() if resp else None

    async def get_events(self) -> dict | None:
        resp = await self._try_request("/liveclientdata/eventdata")
        return resp.json() if resp else None
