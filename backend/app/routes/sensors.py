"""Sensor API routes."""

from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import SensorConfig
from app.schemas.events import ReadingsResponse, SensorBaseline
from app.services import get_all_sensors, get_sensor_by_id
from app.services.baseline_service import get_sensor_baseline
from app.services.readings_service import get_sensor_readings

# Maximum time range limits
MAX_READINGS_DAYS = 30
MAX_BASELINE_HOURS = 168  # 7 days

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@router.get("", response_model=list[SensorConfig])
async def list_sensors(session: AsyncSession = Depends(get_db)) -> list[SensorConfig]:
    """Get all sensors with current readings, 24h trends, and stats."""
    return await get_all_sensors(session)


@router.get("/{sensor_id}", response_model=SensorConfig)
async def get_sensor(
    sensor_id: str,
    session: AsyncSession = Depends(get_db),
) -> SensorConfig:
    """Get a single sensor by ID."""
    sensor = await get_sensor_by_id(session, sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor


@router.get("/{sensor_id}/readings", response_model=ReadingsResponse)
async def get_readings(
    sensor_id: str,
    start: datetime | None = Query(None, description="Start of time range (ISO format)"),
    end: datetime | None = Query(None, description="End of time range (ISO format)"),
    interval: Literal["raw", "1h", "1d"] = Query("raw", description="Aggregation interval"),
    session: AsyncSession = Depends(get_db),
) -> ReadingsResponse:
    """Get historical readings for a sensor with optional time range and aggregation."""
    # Default to last 24 hours if not specified
    now = datetime.now(UTC).replace(tzinfo=None)  # Use naive UTC for SQLite
    if end is None:
        end = now
    if start is None:
        start = end - timedelta(hours=24)

    # Validate time range
    if start >= end:
        raise HTTPException(status_code=400, detail="start must be before end")

    # Enforce maximum time range
    max_range = timedelta(days=MAX_READINGS_DAYS)
    if end - start > max_range:
        raise HTTPException(
            status_code=400,
            detail=f"Time range cannot exceed {MAX_READINGS_DAYS} days",
        )

    result = await get_sensor_readings(session, sensor_id, start, end, interval)
    if not result:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return result


@router.get("/{sensor_id}/baseline", response_model=SensorBaseline)
async def get_baseline(
    sensor_id: str,
    hours: int = Query(24, ge=1, le=168, description="Hours of data to compute baseline from"),
    session: AsyncSession = Depends(get_db),
) -> SensorBaseline:
    """Get baseline statistics for a sensor."""
    result = await get_sensor_baseline(session, sensor_id, hours)
    if not result:
        raise HTTPException(status_code=404, detail="Sensor not found or no data")
    return result
