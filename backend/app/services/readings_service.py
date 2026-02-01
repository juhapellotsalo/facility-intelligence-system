"""Readings service layer — fetches historical sensor readings."""

from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import Integer, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Sensor
from app.schemas.events import ReadingPoint, ReadingsResponse
from app.services._registry import SENSOR_TYPE_REGISTRY

__all__ = ["get_sensor_readings"]

Interval = Literal["raw", "1h", "1d"]


async def get_sensor_readings(
    session: AsyncSession,
    sensor_id: str,
    start: datetime,
    end: datetime,
    interval: Interval = "raw",
) -> ReadingsResponse | None:
    """
    Fetch historical readings for a sensor with optional aggregation.

    Intervals:
    - "raw": Raw readings at their native interval
    - "1h": Hourly averages
    - "1d": Daily averages
    """
    # Get sensor to determine type
    sensor_result = await session.execute(select(Sensor).where(Sensor.id == sensor_id))
    sensor = sensor_result.scalar_one_or_none()
    if not sensor:
        return None

    config = SENSOR_TYPE_REGISTRY.get(sensor.sensor_type)
    if not config:
        return None

    if interval == "raw":
        readings = await _get_raw_readings(session, sensor, config, start, end)
    elif interval == "1h":
        readings = await _get_aggregated_readings(
            session, sensor, config, start, end, "%Y-%m-%d %H:00:00", timedelta(hours=1)
        )
    elif interval == "1d":
        readings = await _get_aggregated_readings(
            session, sensor, config, start, end, "%Y-%m-%d", timedelta(days=1)
        )
    else:
        readings = await _get_raw_readings(session, sensor, config, start, end)

    return ReadingsResponse(
        sensor_id=sensor_id,
        sensor_type=sensor.sensor_type,
        interval=interval,
        readings=readings,
    )


async def _get_raw_readings(
    session: AsyncSession,
    sensor: Sensor,
    config,
    start: datetime,
    end: datetime,
) -> list[ReadingPoint]:
    """Fetch raw readings without aggregation."""
    model = config.model

    query = (
        select(model)
        .where(
            and_(
                model.sensor_id == sensor.id,
                model.timestamp >= start,
                model.timestamp <= end,
            )
        )
        .order_by(model.timestamp)
    )

    result = await session.execute(query)
    readings: list[ReadingPoint] = []

    for row in result.scalars():
        # Get the primary value
        value_attr = config.value_column.key
        value = getattr(row, value_attr)

        # Convert boolean to float for consistency
        if isinstance(value, bool):
            value = float(value)

        # Get secondary value if exists (e.g., humidity)
        humidity = None
        if config.secondary_column is not None:
            humidity = getattr(row, config.secondary_column.key, None)

        readings.append(
            ReadingPoint(
                timestamp=row.timestamp,
                value=value,
                humidity=humidity,
            )
        )

    return readings


async def _get_aggregated_readings(
    session: AsyncSession,
    sensor: Sensor,
    config,
    start: datetime,
    end: datetime,
    strftime_format: str,
    bucket_delta: timedelta,
) -> list[ReadingPoint]:
    """Fetch readings aggregated by time bucket using GROUP BY."""
    model = config.model

    if config.supports_aggregation:
        # For numeric sensors: compute averages
        query = (
            select(
                func.strftime(strftime_format, model.timestamp).label("bucket"),
                func.avg(config.value_column).label("avg_value"),
            )
            .where(
                and_(
                    model.sensor_id == sensor.id,
                    model.timestamp >= start,
                    model.timestamp <= end,
                )
            )
            .group_by(func.strftime(strftime_format, model.timestamp))
            .order_by(func.strftime(strftime_format, model.timestamp))
        )
    else:
        # For boolean sensors: count events
        query = (
            select(
                func.strftime(strftime_format, model.timestamp).label("bucket"),
                func.sum(func.cast(config.value_column, Integer)).label("avg_value"),
            )
            .where(
                and_(
                    model.sensor_id == sensor.id,
                    model.timestamp >= start,
                    model.timestamp <= end,
                )
            )
            .group_by(func.strftime(strftime_format, model.timestamp))
            .order_by(func.strftime(strftime_format, model.timestamp))
        )

    result = await session.execute(query)
    readings: list[ReadingPoint] = []

    for row in result:
        bucket_str, avg_value = row
        if avg_value is not None:
            # Parse the bucket string back to datetime
            if bucket_delta == timedelta(hours=1):
                timestamp = datetime.strptime(bucket_str, "%Y-%m-%d %H:%M:%S")
            else:
                timestamp = datetime.strptime(bucket_str, "%Y-%m-%d")

            readings.append(ReadingPoint(timestamp=timestamp, value=round(float(avg_value), 2)))

    return readings
