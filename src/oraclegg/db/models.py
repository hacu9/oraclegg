from datetime import datetime

from sqlalchemy import Boolean, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Champion(Base):
    __tablename__ = "champions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Riot champion ID
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    key: Mapped[str] = mapped_column(String(64), nullable=False)  # Internal key e.g. "Aatrox"
    tags: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array: ["Fighter","Tank"]
    stats: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: Meraki stats blob
    abilities: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: ability data
    patch: Mapped[str] = mapped_column(String(16), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Riot item ID
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    stats: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: item stats
    tags: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    gold_total: Mapped[int] = mapped_column(Integer, nullable=False)
    gold_base: Mapped[int] = mapped_column(Integer, nullable=False)
    builds_from: Mapped[str | None] = mapped_column(Text)  # JSON array of item IDs
    builds_into: Mapped[str | None] = mapped_column(Text)  # JSON array of item IDs
    patch: Mapped[str] = mapped_column(String(16), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())


class BuildAggregate(Base):
    __tablename__ = "build_aggregates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    champion_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # TOP, JUNGLE, MID, ADC, SUPPORT
    enemy_comp_archetype: Mapped[str] = mapped_column(String(32), nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)

    # Build path: ordered items
    item_build_path: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array of item IDs
    boots_id: Mapped[int | None] = mapped_column(Integer)

    # Skill order
    skill_order: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: first 18 levels
    skill_max_order: Mapped[str] = mapped_column(String(16), nullable=False)  # e.g. "Q>E>W"

    # Starting items + summoners + runes
    starting_items: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    summoner_spells: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    primary_rune_tree: Mapped[str] = mapped_column(String(32), nullable=False)
    primary_keystone: Mapped[int] = mapped_column(Integer, nullable=False)
    primary_runes: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    secondary_rune_tree: Mapped[str] = mapped_column(String(32), nullable=False)
    secondary_runes: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    stat_shards: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array

    # Metadata
    patch: Mapped[str] = mapped_column(String(16), nullable=False)
    region: Mapped[str] = mapped_column(String(8), default="all")
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    __table_args__ = (
        Index("idx_build_agg_lookup", "champion_id", "role", "enemy_comp_archetype", "patch"),
    )


class PlayerCache(Base):
    __tablename__ = "player_cache"

    puuid: Mapped[str] = mapped_column(String(78), primary_key=True)
    game_name: Mapped[str] = mapped_column(String(64), nullable=False)
    tag_line: Mapped[str] = mapped_column(String(8), nullable=False)
    summoner_id: Mapped[str | None] = mapped_column(String(64))
    rank_solo: Mapped[str | None] = mapped_column(String(32))
    rank_flex: Mapped[str | None] = mapped_column(String(32))
    profile_icon_id: Mapped[int | None] = mapped_column(Integer)
    summoner_level: Mapped[int | None] = mapped_column(Integer)
    last_fetched: Mapped[datetime] = mapped_column(nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: full scouting report


class MatchHistoryCache(Base):
    __tablename__ = "match_history_cache"

    match_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: full match DTO
    fetched_at: Mapped[datetime] = mapped_column(default=func.now())


class ScoutingReport(Base):
    __tablename__ = "scouting_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str | None] = mapped_column(String(32))
    timestamp: Mapped[datetime] = mapped_column(default=func.now())
    our_team: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    enemy_team: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    recommendations: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    phase: Mapped[str] = mapped_column(String(16), default="champ_select")


class PersonalMatch(Base):
    __tablename__ = "personal_matches"

    match_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    champion_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    win: Mapped[bool] = mapped_column(Boolean, nullable=False)
    kills: Mapped[int | None] = mapped_column(Integer)
    deaths: Mapped[int | None] = mapped_column(Integer)
    assists: Mapped[int | None] = mapped_column(Integer)
    cs: Mapped[int | None] = mapped_column(Integer)
    cs_per_min: Mapped[float | None] = mapped_column(Float)
    vision_score: Mapped[int | None] = mapped_column(Integer)
    damage_dealt: Mapped[int | None] = mapped_column(Integer)
    damage_taken: Mapped[int | None] = mapped_column(Integer)
    gold_earned: Mapped[int | None] = mapped_column(Integer)
    game_duration: Mapped[int | None] = mapped_column(Integer)  # seconds
    items_final: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    enemy_champion_ids: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    timeline_summary: Mapped[str | None] = mapped_column(Text)  # JSON
    played_at: Mapped[datetime] = mapped_column(nullable=False)
    patch: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = (
        Index("idx_personal_champion", "champion_id", "played_at"),
    )


class GameSnapshot(Base):
    __tablename__ = "game_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str | None] = mapped_column(String(32))
    game_time_secs: Mapped[float] = mapped_column(Float, nullable=False)
    snapshot_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    tips_generated: Mapped[str | None] = mapped_column(Text)  # JSON
    created_at: Mapped[datetime] = mapped_column(default=func.now())


class UserSetting(Base):
    __tablename__ = "user_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class Rune(Base):
    __tablename__ = "runes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Riot rune/perk ID
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    tree_id: Mapped[int] = mapped_column(Integer, nullable=False)  # Parent tree ID
    tree_name: Mapped[str] = mapped_column(String(32), nullable=False)
    slot: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=keystone, 1-3=rows
    icon: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    patch: Mapped[str] = mapped_column(String(16), nullable=False)
