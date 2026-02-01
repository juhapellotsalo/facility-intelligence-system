#!/usr/bin/env python3
"""Generate 48 hours of sensor readings with Cold Room B incident baked in."""

import asyncio
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database import async_session
from app.models import (
    AirQualityReading,
    DoorReading,
    EnvironmentalReading,
    MotionReading,
    Sensor,
)

# Fixed seed for reproducibility
RANDOM_SEED = 42

# Time configuration
HOURS_TO_GENERATE = 48
INTERVAL_MINUTES = 15

# Sensor baselines
TEMP_BASELINES = {
    "loading-temp": (18.0, 45.0),  # (temp, humidity)
    "cold-a-temp": (3.0, 82.0),
    "cold-b-temp": (-17.0, 68.0),
    "dry-temp": (17.8, 38.0),
}

AQ_BASELINES = {
    "loading-aq": 420.0,  # CO2 ppm
    "dry-aq": 380.0,
}


def generate_environmental_readings(
    sensor_id: str,
    start_time: datetime,
    end_time: datetime,
) -> list[EnvironmentalReading]:
    """Generate environmental (temp/humidity) readings."""
    readings = []
    base_temp, base_humidity = TEMP_BASELINES[sensor_id]
    current_time = start_time
    temp = base_temp
    humidity = base_humidity

    # Cold Room B incident: temperature drift starting 6 hours ago
    incident_start = end_time - timedelta(hours=6)
    is_cold_b = sensor_id == "cold-b-temp"

    while current_time <= end_time:
        # Apply Cold Room B incident drift
        if is_cold_b and current_time >= incident_start:
            # Drift from -17 to -14.2 over 6 hours
            hours_into_incident = (current_time - incident_start).total_seconds() / 3600
            drift = min(2.8, hours_into_incident * 0.47)  # ~0.47°C per hour
            temp = base_temp + drift + random.uniform(-0.2, 0.2)
        else:
            # Normal random walk
            temp = base_temp + random.uniform(-0.3, 0.3)

        humidity = base_humidity + random.uniform(-2, 2)

        readings.append(
            EnvironmentalReading(
                sensor_id=sensor_id,
                timestamp=current_time,
                temperature=round(temp, 1),
                humidity=round(humidity, 1),
            )
        )
        current_time += timedelta(minutes=INTERVAL_MINUTES)

    return readings


def generate_air_quality_readings(
    sensor_id: str,
    start_time: datetime,
    end_time: datetime,
) -> list[AirQualityReading]:
    """Generate air quality (CO2) readings."""
    readings = []
    base_co2 = AQ_BASELINES[sensor_id]
    current_time = start_time

    while current_time <= end_time:
        # Small random variation
        co2 = base_co2 + random.uniform(-30, 30)
        readings.append(
            AirQualityReading(
                sensor_id=sensor_id,
                timestamp=current_time,
                co2_ppm=round(co2, 0),
            )
        )
        current_time += timedelta(minutes=INTERVAL_MINUTES)

    return readings


def generate_door_readings(
    sensor_id: str,
    start_time: datetime,
    end_time: datetime,
) -> list[DoorReading]:
    """Generate door open/closed readings."""
    readings = []
    current_time = start_time
    is_open = False

    # Door opens occasionally during business hours
    while current_time <= end_time:
        hour = current_time.hour

        # Higher chance of door activity during business hours (6am-6pm)
        if 6 <= hour <= 18:
            # ~5% chance of state change per 15-min interval
            if random.random() < 0.05:
                is_open = not is_open
        else:
            # Doors mostly closed at night
            if is_open and random.random() < 0.3:
                is_open = False

        readings.append(
            DoorReading(
                sensor_id=sensor_id,
                timestamp=current_time,
                is_open=is_open,
            )
        )
        current_time += timedelta(minutes=INTERVAL_MINUTES)

    return readings


def generate_motion_readings(
    sensor_id: str,
    start_time: datetime,
    end_time: datetime,
) -> list[MotionReading]:
    """Generate motion detection readings."""
    readings = []
    current_time = start_time

    while current_time <= end_time:
        hour = current_time.hour

        # Motion more likely during business hours
        if 6 <= hour <= 18:
            motion = random.random() < 0.15  # 15% chance during work hours
        else:
            motion = random.random() < 0.02  # 2% chance at night

        readings.append(
            MotionReading(
                sensor_id=sensor_id,
                timestamp=current_time,
                motion_detected=motion,
            )
        )
        current_time += timedelta(minutes=INTERVAL_MINUTES)

    return readings


async def generate_all_data() -> None:
    """Generate 48 hours of sensor data."""
    random.seed(RANDOM_SEED)

    end_time = datetime.now().replace(second=0, microsecond=0)
    start_time = end_time - timedelta(hours=HOURS_TO_GENERATE)

    print(f"Generating data from {start_time} to {end_time}")

    async with async_session() as session:
        # Check if data already exists
        result = await session.execute(select(EnvironmentalReading).limit(1))
        if result.scalar_one_or_none():
            print("Data already exists. Run with --reset to regenerate.")
            return

        # Get all sensors
        result = await session.execute(select(Sensor))
        sensors = result.scalars().all()

        total_readings = 0

        for sensor in sensors:
            if sensor.sensor_type == "environmental":
                readings = generate_environmental_readings(sensor.id, start_time, end_time)
                session.add_all(readings)
                total_readings += len(readings)

            elif sensor.sensor_type == "air_quality":
                readings = generate_air_quality_readings(sensor.id, start_time, end_time)
                session.add_all(readings)
                total_readings += len(readings)

            elif sensor.sensor_type == "door":
                readings = generate_door_readings(sensor.id, start_time, end_time)
                session.add_all(readings)
                total_readings += len(readings)

            elif sensor.sensor_type == "motion":
                readings = generate_motion_readings(sensor.id, start_time, end_time)
                session.add_all(readings)
                total_readings += len(readings)

        await session.commit()
        print(f"Generated {total_readings} readings for {len(sensors)} sensors.")


async def clear_readings() -> None:
    """Clear all reading data."""
    async with async_session() as session:
        await session.execute(EnvironmentalReading.__table__.delete())
        await session.execute(AirQualityReading.__table__.delete())
        await session.execute(DoorReading.__table__.delete())
        await session.execute(MotionReading.__table__.delete())
        await session.commit()
    print("Cleared all readings.")


async def reset_and_generate() -> None:
    """Clear existing data and regenerate."""
    await clear_readings()
    await generate_all_data()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        asyncio.run(reset_and_generate())
    else:
        asyncio.run(generate_all_data())
