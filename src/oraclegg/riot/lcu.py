"""League Client Update (LCU) API client.

Connects to the local League client via lockfile auth.
Provides champ select detection and WebSocket event subscriptions.
"""

import asyncio
import base64
import json
import logging
import platform
import ssl
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Known League install paths
LOCKFILE_PATHS = {
    "Windows": [
        Path("C:/Riot Games/League of Legends/lockfile"),
        Path("D:/Riot Games/League of Legends/lockfile"),
    ],
    "Linux": [
        # WSL2 paths (League runs on Windows, lockfile accessible via /mnt/c)
        Path("/mnt/c/Riot Games/League of Legends/lockfile"),
        Path("/mnt/d/Riot Games/League of Legends/lockfile"),
    ],
    "Darwin": [  # macOS
        Path("/Applications/League of Legends.app/Contents/LoL/lockfile"),
    ],
}


def find_lockfile(custom_path: str = "") -> Path | None:
    """Find the LCU lockfile on disk."""
    if custom_path:
        p = Path(custom_path) / "lockfile"
        return p if p.exists() else None

    system = platform.system()
    for path in LOCKFILE_PATHS.get(system, []):
        if path.exists():
            return path
    return None


def parse_lockfile(path: Path) -> dict:
    """Parse lockfile: processName:pid:port:password:protocol"""
    content = path.read_text().strip()
    parts = content.split(":")
    return {
        "process": parts[0],
        "pid": int(parts[1]),
        "port": int(parts[2]),
        "password": parts[3],
        "protocol": parts[4],
    }


class LCUClient:
    """Client for the League Client Update API (local)."""

    def __init__(self):
        self.port: int | None = None
        self.password: str | None = None
        self._client: httpx.AsyncClient | None = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self, custom_path: str = "") -> bool:
        """Find lockfile and establish connection."""
        lockfile = find_lockfile(custom_path)
        if not lockfile:
            self._connected = False
            return False

        try:
            creds = parse_lockfile(lockfile)
            self.port = creds["port"]
            self.password = creds["password"]

            auth = base64.b64encode(f"riot:{self.password}".encode()).decode()

            # On WSL, use Windows host IP since LCU binds to Windows localhost
            host = "127.0.0.1"
            try:
                with open("/proc/version", "r") as f:
                    if "microsoft" in f.read().lower():
                        # Try Windows gateway IP
                        import subprocess
                        result = subprocess.run(
                            ["ip", "route", "show", "default"],
                            capture_output=True, text=True, timeout=2,
                        )
                        for word in result.stdout.split():
                            if word.count(".") == 3:
                                host = word
                                break
            except Exception:
                pass

            self._client = httpx.AsyncClient(
                base_url=f"https://{host}:{self.port}",
                headers={"Authorization": f"Basic {auth}"},
                verify=False,  # LCU uses self-signed cert
                timeout=httpx.Timeout(10.0),
            )

            # Verify connection
            resp = await self._client.get("/lol-summoner/v1/current-summoner")
            self._connected = resp.status_code == 200
            if self._connected:
                logger.info(f"Connected to LCU on port {self.port}")
            return self._connected
        except Exception as e:
            logger.debug(f"LCU connection failed: {e}")
            self._connected = False
            return False

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._connected = False

    async def get(self, endpoint: str) -> dict | list | None:
        """Make a GET request to the LCU API."""
        if not self._client or not self._connected:
            return None
        try:
            resp = await self._client.get(endpoint)
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            logger.debug(f"LCU GET {endpoint} failed: {e}")
            return None

    async def get_champ_select_session(self) -> dict | None:
        """Get the current champ select session data."""
        return await self.get("/lol-champ-select/v1/session")

    async def get_current_summoner(self) -> dict | None:
        return await self.get("/lol-summoner/v1/current-summoner")

    async def get_gameflow_phase(self) -> str | None:
        """Get current gameflow phase: None, Lobby, ChampSelect, InProgress, etc."""
        result = await self.get("/lol-gameflow/v1/gameflow-phase")
        return result if isinstance(result, str) else None

    async def subscribe_champ_select(self, callback):
        """Subscribe to champ select WebSocket events.

        Uses simple polling as a reliable alternative to WebSocket subscription.
        """
        import websockets

        if not self.port or not self.password:
            return

        auth = base64.b64encode(f"riot:{self.password}".encode()).decode()
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        uri = f"wss://127.0.0.1:{self.port}"
        try:
            async with websockets.connect(
                uri,
                additional_headers={"Authorization": f"Basic {auth}"},
                ssl=ssl_context,
            ) as ws:
                # Subscribe to champ select events
                await ws.send(json.dumps([5, "OnJsonApiEvent_lol-champ-select_v1_session"]))
                logger.info("Subscribed to champ select WebSocket events")

                async for message in ws:
                    try:
                        data = json.loads(message)
                        if isinstance(data, list) and len(data) >= 3:
                            await callback(data[2])
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            logger.debug(f"WebSocket subscription ended: {e}")
