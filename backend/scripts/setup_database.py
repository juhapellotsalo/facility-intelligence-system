#!/usr/bin/env python3
"""One-shot database setup: init tables, seed zones/sensors, generate data."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_data import generate_all_data
from scripts.init_db import init_db
from scripts.seed_zones import seed_zones_and_sensors


async def setup_all() -> None:
    """Run all setup steps."""
    print("=== Setting up Facility Intelligence System database ===")
    print()

    print("Step 1: Creating tables...")
    await init_db()
    print()

    print("Step 2: Seeding zones and sensors...")
    await seed_zones_and_sensors()
    print()

    print("Step 3: Generating sensor data (48h)...")
    await generate_all_data()
    print()

    print("=== Setup complete! ===")
    print("Start the server with: uvicorn app.main:app --reload --port 8000")


if __name__ == "__main__":
    asyncio.run(setup_all())
