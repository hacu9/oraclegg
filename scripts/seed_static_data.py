"""Seed champion and item data from Data Dragon + Meraki Analytics."""

import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

from oraclegg.db.engine import init_db
from oraclegg.static_data.manager import seed_all


async def main():
    print("\n  OracleGG — Seeding static data (champions + items)\n")

    try:
        await init_db()
    except Exception as e:
        print(f"ERROR: Failed to initialize database: {e}")
        print("  Check that the data directory is writable.")
        sys.exit(1)

    try:
        await seed_all()
        print("\n  Static data seeded successfully.\n")
    except Exception as e:
        print(f"\nERROR: Seeding failed: {e}")
        print("  Check your internet connection (DDragon must be reachable).")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
