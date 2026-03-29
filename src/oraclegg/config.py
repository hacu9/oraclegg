from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Riot API
    riot_api_key: str = "RGAPI-change-me"
    riot_region: str = "americas"  # americas, europe, asia, sea
    riot_platform: str = "la1"  # na1, la1, la2, euw1, kr, etc.
    summoner_riot_id: str = "Mistyck#Lan"

    # League client path (auto-detected if empty)
    lcu_path: str = ""

    # Database
    db_path: str = "./data/oraclegg.db"

    # Polling intervals (seconds)
    live_client_poll_interval: int = 3
    lcu_poll_interval: int = 2

    # Tip engine
    tip_cooldown_seconds: int = 15
    max_tips_per_minute: int = 4

    # Data pipeline
    pipeline_region: str = "na1"
    pipeline_player_sample_size: int = 500
    pipeline_matches_per_player: int = 10
    pipeline_min_sample_size: int = 30

    # DDragon (updated on startup)
    ddragon_version: str = "14.10.1"

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    @property
    def ddragon_base(self) -> str:
        return f"https://ddragon.leagueoflegends.com/cdn/{self.ddragon_version}/img"

    @property
    def db_url(self) -> str:
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{path}"

    @property
    def riot_base_url(self) -> str:
        """Regional routing for match-v5, account-v1, etc."""
        return f"https://{self.riot_region}.api.riotgames.com"

    @property
    def platform_base_url(self) -> str:
        """Platform routing for summoner-v4, league-v4, etc."""
        return f"https://{self.riot_platform}.api.riotgames.com"

    @property
    def summoner_name(self) -> str:
        return self.summoner_riot_id.split("#")[0]

    @property
    def summoner_tag(self) -> str:
        return self.summoner_riot_id.split("#")[1] if "#" in self.summoner_riot_id else ""


settings = Settings()
