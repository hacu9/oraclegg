"""Pydantic models for Riot API responses."""

from pydantic import BaseModel


class AccountDTO(BaseModel):
    puuid: str
    gameName: str | None = None
    tagLine: str | None = None


class SummonerDTO(BaseModel):
    id: str | None = None
    accountId: str | None = None
    puuid: str
    profileIconId: int
    revisionDate: int | None = None
    summonerLevel: int


class LeagueEntryDTO(BaseModel):
    leagueId: str | None = None
    summonerId: str
    queueType: str
    tier: str | None = None
    rank: str | None = None
    leaguePoints: int = 0
    wins: int = 0
    losses: int = 0
    hotStreak: bool = False
    freshBlood: bool = False
    inactive: bool = False


class ChampionMasteryDTO(BaseModel):
    championId: int
    championLevel: int
    championPoints: int
    lastPlayTime: int | None = None


class MatchParticipantDTO(BaseModel):
    puuid: str
    summonerName: str = ""
    riotIdGameName: str | None = None
    riotIdTagline: str | None = None
    championId: int
    championName: str
    teamId: int = 100
    teamPosition: str = ""  # TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY
    individualPosition: str = ""
    win: bool
    kills: int
    deaths: int
    assists: int
    totalMinionsKilled: int
    neutralMinionsKilled: int
    visionScore: int
    totalDamageDealtToChampions: int
    totalDamageTaken: int
    goldEarned: int
    item0: int
    item1: int
    item2: int
    item3: int
    item4: int
    item5: int
    item6: int  # trinket
    summoner1Id: int
    summoner2Id: int
    # Runes
    perks: dict | None = None
    # Skill order from timeline
    skillOrder: list[str] | None = None  # We populate this from timeline data


class MatchInfoDTO(BaseModel):
    gameId: int
    gameCreation: int
    gameDuration: int
    gameVersion: str
    queueId: int
    participants: list[MatchParticipantDTO]


class MatchDTO(BaseModel):
    metadata: dict
    info: MatchInfoDTO
