"""Import your recent match history into the tracking database.

Usage: uv run python scripts/import_history.py [--count 20]
"""

import argparse
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

from oraclegg.config import settings
from oraclegg.db.engine import init_db
from oraclegg.riot.client import RiotClient
from oraclegg.tracker.post_game import analyze_post_game


async def main(count: int):
    await init_db()
    client = RiotClient()

    try:
        name, tag = settings.summoner_riot_id.split("#")
        account = await client.get_account_by_riot_id(name, tag)
        print(f"Importing history for {account.gameName}#{account.tagLine}")

        match_ids = await client.get_match_ids(account.puuid, queue=420, count=count)
        print(f"Found {len(match_ids)} ranked matches")

        imported = 0
        for mid in match_ids:
            # analyze_post_game gets the most recent — we need to fetch each
            try:
                match = await client.get_match(mid)
                info = match.info

                me = None
                for p in info.participants:
                    if p.puuid == account.puuid:
                        me = p
                        break

                if not me:
                    continue

                import json
                from datetime import datetime
                from oraclegg.db.engine import async_session
                from oraclegg.db.models import PersonalMatch
                from sqlalchemy import select

                async with async_session() as session:
                    existing = await session.execute(
                        select(PersonalMatch).where(PersonalMatch.match_id == mid)
                    )
                    if existing.scalar_one_or_none():
                        continue

                cs = me.totalMinionsKilled + me.neutralMinionsKilled
                game_mins = info.gameDuration / 60
                role = me.teamPosition or "UNKNOWN"
                role_map = {"MIDDLE": "MID", "BOTTOM": "ADC", "UTILITY": "SUPPORT"}
                role = role_map.get(role, role)

                items = [getattr(me, f"item{i}") for i in range(7) if getattr(me, f"item{i}", 0) > 0]
                enemy_ids = [
                    p.championId for p in info.participants
                    if p.teamId != me.teamId
                ]

                personal = PersonalMatch(
                    match_id=mid,
                    champion_id=me.championId,
                    role=role,
                    win=me.win,
                    kills=me.kills,
                    deaths=me.deaths,
                    assists=me.assists,
                    cs=cs,
                    cs_per_min=round(cs / max(game_mins, 1), 1),
                    vision_score=me.visionScore,
                    damage_dealt=me.totalDamageDealtToChampions,
                    damage_taken=me.totalDamageTaken,
                    gold_earned=me.goldEarned,
                    game_duration=info.gameDuration,
                    items_final=json.dumps(items),
                    enemy_champion_ids=json.dumps(enemy_ids),
                    played_at=datetime.fromtimestamp(info.gameCreation / 1000),
                    patch=info.gameVersion[:8],
                )
                async with async_session() as session:
                    await session.merge(personal)
                    await session.commit()

                result = "W" if me.win else "L"
                print(f"  {me.championName} {me.kills}/{me.deaths}/{me.assists} {result} - {mid}")
                imported += 1

            except Exception as e:
                print(f"  Error on {mid}: {e}")

        print(f"\nImported {imported} matches")

    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=20)
    args = parser.parse_args()
    asyncio.run(main(args.count))
