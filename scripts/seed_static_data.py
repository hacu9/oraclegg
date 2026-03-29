"""Seed champion and item data from Data Dragon + Meraki Analytics."""

import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

from oraclegg.db.engine import init_db
from oraclegg.static_data.manager import seed_all


async def main():
    await init_db()
    await seed_all()


if __name__ == "__main__":
    asyncio.run(main())
