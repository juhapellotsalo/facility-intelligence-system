"""Baseline service layer — computes statistical baselines from sensor readings."""

import math
from datetime import datetime, timedelta

from sqlalchemy import Integer, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Sensor
from app.schemas.events import HourlyBaseline, SensorBaseline
from app.services._registry import SENSOR_TYPE_REGISTRY

__all__ = ["get_sensor_baseline", "get_hourly_baselines"]

# Constants
DEFAULT_BASELINE_HOURS = 24
DEFAULT_BASELINE_DAYS = 7


async def get_sensor_baseline(
    session: AsyncSession,
    sensor_id: str,
    hours: int = DEFAULT_BASELINE_HOURS,
) -> SensorBaseline | None:
    """
    Compute baseline statistics for a sensor over the specified period.

    Returns mean, std_dev, min, max computed from the raw readings.
    Only supports numeric sensor types (environmental, air_quality).
    """
    if hours <= 0:
        return None

    # Get sensor to determine type
    sensor_result = await session.execute(select(Sensor).where(Sensor.id == sensor_id))
    sensor = sensor_result.scalar_one_or_none()
    if not sensor:
        return None

    config = SENSOR_TYPE_REGISTRY.get(sensor.sensor_type)
    if not config or not config.supports_aggregation:
        # Door and motion sensors don't have meaningful numeric baselines
        return None

    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    model = config.model

    # Single query to get count, avg, min, max
    result = await session.execute(
        select(
            func.count(model.id),
            func.avg(config.value_column),
            func.min(config.value_column),
            func.max(config.value_column),
        ).where(
            and_(
                model.sensor_id == sensor_id,
                model.timestamp >= start_time,
                model.timestamp <= end_time,
            )
        )
    )
    row = result.one()
    count, avg, min_val, max_val = row

    if count == 0 or avg is None:
        return None

    # Compute standard deviation (SQLite doesn't have built-in stdev)
    std_dev = await _compute_std_dev(
        session, model, config.value_column, sensor_id, start_time, end_time, avg
    )

    precision = 2 if config.unit == "°C" else 1
    return SensorBaseline(
        sensor_id=sensor_id,
        mean=round(avg, precision),
        std_dev=round(std_dev, precision),
        min=round(min_val, precision),
        max=round(max_val, precision),
        unit=config.unit,
        sample_count=count,
        period_hours=hours,
    )


async def _compute_std_dev(
    session: AsyncSession,
    model: type,
    value_column,
    sensor_id: str,
    start_time: datetime,
    end_time: datetime,
    mean: float,
) -> float:
    """
    Compute standard deviation manually since SQLite lacks built-in stdev.

    Uses the formula: sqrt(avg((value - mean)^2))
    """
    result = await session.execute(
        select(func.avg(func.pow(value_column - mean, 2))).where(
            and_(
                model.sensor_id == sensor_id,
                model.timestamp >= start_time,
                model.timestamp <= end_time,
            )
        )
    )
    variance = result.scalar()

    if variance is None or variance < 0:
        return 0.0

    return math.sqrt(variance)


async def get_hourly_baselines(
    session: AsyncSession,
    sensor_id: str,
    days: int = DEFAULT_BASELINE_DAYS,
) -> list[HourlyBaseline]:
    """
    Compute per-hour-of-day baselines for time-of-day pattern analysis.

    Returns 24 entries (one per hour 0-23) with mean and std_dev
    computed from readings at that hour across multiple days.
    Uses a single GROUP BY query instead of 24+ separate queries.
    """
    if days <= 0:
        return []

    # Get sensor to determine type
    sensor_result = await session.execute(select(Sensor).where(Sensor.id == sensor_id))
    sensor = sensor_result.scalar_one_or_none()
    if not sensor:
        return []

    config = SENSOR_TYPE_REGISTRY.get(sensor.sensor_type)
    if not config or not config.supports_aggregation:
        # Return empty baselines for non-numeric sensors
        return [HourlyBaseline(hour=h, mean=0.0, std_dev=0.0, sample_count=0) for h in range(24)]

    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    model = config.model

    # Single query with GROUP BY hour to get counts and averages
    result = await session.execute(
        select(
            func.cast(func.strftime("%H", model.timestamp), Integer).label("hour"),
            func.count(model.id).label("cnt"),
            func.avg(config.value_column).label("avg_value"),
        )
        .where(
            and_(
                model.sensor_id == sensor_id,
                model.timestamp >= start_time,
                model.timestamp <= end_time,
            )
        )
        .group_by(func.strftime("%H", model.timestamp))
    )

    # Build a lookup of hour -> (count, avg)
    hourly_stats: dict[int, tuple[int, float]] = {}
    for row in result:
        hour, count, avg = row
        if avg is not None:
            hourly_stats[hour] = (count, float(avg))

    # Now compute std_dev for each hour that has data
    # Single query to get variance per hour
    var_result = await session.execute(
        select(
            func.cast(func.strftime("%H", model.timestamp), Integer).label("hour"),
            func.avg(
                func.pow(
                    config.value_column
                    - func.avg(config.value_column).over(
                        partition_by=func.strftime("%H", model.timestamp)
                    ),
                    2,
                )
            ).label("variance"),
        )
        .where(
            and_(
                model.sensor_id == sensor_id,
                model.timestamp >= start_time,
                model.timestamp <= end_time,
            )
        )
        .group_by(func.strftime("%H", model.timestamp))
    )

    hourly_variance: dict[int, float] = {}
    for row in var_result:
        hour, variance = row
        if variance is not None:
            hourly_variance[hour] = float(variance)

    # Build the result list for all 24 hours
    precision = 2 if config.unit == "°C" else 1
    baselines: list[HourlyBaseline] = []

    for hour in range(24):
        if hour in hourly_stats:
            count, avg = hourly_stats[hour]
            variance = hourly_variance.get(hour, 0.0)
            std_dev = math.sqrt(variance) if variance > 0 else 0.0
            baselines.append(
                HourlyBaseline(
                    hour=hour,
                    mean=round(avg, precision),
                    std_dev=round(std_dev, precision),
                    sample_count=count,
                )
            )
        else:
            baselines.append(HourlyBaseline(hour=hour, mean=0.0, std_dev=0.0, sample_count=0))

    return baselines
