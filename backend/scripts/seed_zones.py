#!/usr/bin/env python3
"""Seed zones and sensors into the database."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database import async_session
from app.models import Sensor, Zone

# Zone definitions matching frontend layout
ZONES = [
    {
        "id": "loading",
        "name": "Loading Bay",
        "zone_type": "ambient",
        "target_temp_min": 15.0,
        "target_temp_max": 25.0,
    },
    {
        "id": "cold-a",
        "name": "Cold Room A — Fresh",
        "zone_type": "cold_fresh",
        "target_temp_min": 2.0,
        "target_temp_max": 4.0,
    },
    {
        "id": "cold-b",
        "name": "Cold Room B — Frozen",
        "zone_type": "cold_frozen",
        "target_temp_min": -20.0,
        "target_temp_max": -16.0,
    },
    {
        "id": "dry",
        "name": "Dry Storage",
        "zone_type": "dry_storage",
        "target_temp_min": 15.0,
        "target_temp_max": 20.0,
    },
]

# Sensor definitions matching frontend SENSORS array
SENSORS = [
    # Loading Bay
    {
        "id": "loading-temp",
        "zone_id": "loading",
        "sensor_type": "environmental",
        "label": "Temperature & Humidity",
        "warning_threshold": 25.0,
        "critical_threshold": 30.0,
    },
    {
        "id": "loading-aq",
        "zone_id": "loading",
        "sensor_type": "air_quality",
        "label": "Air Quality (CO₂)",
        "warning_threshold": 800.0,
        "critical_threshold": 1200.0,
    },
    {
        "id": "loading-door",
        "zone_id": "loading",
        "sensor_type": "door",
        "label": "Bay Door",
        "warning_threshold": None,
        "critical_threshold": None,
    },
    {
        "id": "loading-motion",
        "zone_id": "loading",
        "sensor_type": "motion",
        "label": "Dock Motion",
        "warning_threshold": None,
        "critical_threshold": None,
    },
    # Cold Room A — Fresh
    {
        "id": "cold-a-motion",
        "zone_id": "cold-a",
        "sensor_type": "motion",
        "label": "Entry Motion",
        "warning_threshold": None,
        "critical_threshold": None,
    },
    {
        "id": "cold-a-temp",
        "zone_id": "cold-a",
        "sensor_type": "environmental",
        "label": "Temperature & Humidity",
        "warning_threshold": 5.0,
        "critical_threshold": 8.0,
    },
    # Cold Room B — Frozen
    {
        "id": "cold-b-door",
        "zone_id": "cold-b",
        "sensor_type": "door",
        "label": "Freezer Door",
        "warning_threshold": None,
        "critical_threshold": None,
    },
    {
        "id": "cold-b-temp",
        "zone_id": "cold-b",
        "sensor_type": "environmental",
        "label": "Temperature & Humidity",
        "warning_threshold": -18.0,  # Warning if above -18°C
        "critical_threshold": -10.0,  # Critical if above -10°C
    },
    {
        "id": "cold-b-motion",
        "zone_id": "cold-b",
        "sensor_type": "motion",
        "label": "Room Motion",
        "warning_threshold": None,
        "critical_threshold": None,
    },
    # Dry Storage
    {
        "id": "dry-temp",
        "zone_id": "dry",
        "sensor_type": "environmental",
        "label": "Temp & Humidity",
        "warning_threshold": 25.0,
        "critical_threshold": 30.0,
    },
    {
        "id": "dry-aq",
        "zone_id": "dry",
        "sensor_type": "air_quality",
        "label": "Air Quality",
        "warning_threshold": 800.0,
        "critical_threshold": 1200.0,
    },
]


async def seed_zones_and_sensors() -> None:
    """Seed zones and sensors (idempotent)."""
    async with async_session() as session:
        # Check if already seeded
        result = await session.execute(select(Zone).limit(1))
        if result.scalar_one_or_none():
            print("Zones already seeded, skipping.")
        else:
            # Insert zones
            for zone_data in ZONES:
                zone = Zone(**zone_data)
                session.add(zone)
            await session.commit()
            print(f"Seeded {len(ZONES)} zones.")

        # Check if sensors already seeded
        result = await session.execute(select(Sensor).limit(1))
        if result.scalar_one_or_none():
            print("Sensors already seeded, skipping.")
        else:
            # Insert sensors
            for sensor_data in SENSORS:
                sensor = Sensor(**sensor_data)
                session.add(sensor)
            await session.commit()
            print(f"Seeded {len(SENSORS)} sensors.")


if __name__ == "__main__":
    asyncio.run(seed_zones_and_sensors())
