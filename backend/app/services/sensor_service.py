"""Sensor service layer — computes aggregated sensor data for the API."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Sensor, Zone
from app.schemas import SensorConfig, SensorReading, SensorStats, SensorThresholds
from app.services._registry import SENSOR_TYPE_REGISTRY, SensorTypeConfig

# Constants
TREND_HOURS = 24


def compute_status(
    value: float,
    warning_threshold: float | None,
    critical_threshold: float | None,
) -> tuple[str, str]:
    """Compute status and status text based on thresholds.

    For cold rooms (negative thresholds), warning means value is ABOVE threshold.
    For other sensors, warning means value is ABOVE threshold.
    """
    if warning_threshold is None:
        return "normal", "Normal"

    is_warning = value > warning_threshold
    is_critical = critical_threshold is not None and value > critical_threshold

    if is_critical:
        return "critical", "Critical"
    elif is_warning:
        if warning_threshold < 0:
            return "warning", f"Warning — above {warning_threshold}°C target"
        return "warning", "Warning"
    return "normal", "Normal"


def format_reading_value(config: SensorTypeConfig, value: float) -> str:
    """Format reading value with appropriate unit."""
    if config.format_value:
        return config.format_value(value)
    if config.unit == "°C":
        return f"{value}°C"
    if config.unit == "ppm":
        return str(int(value))
    return str(value)


def format_reading_unit(config: SensorTypeConfig, secondary_value: float | None) -> str | None:
    """Format secondary unit (humidity for environmental, ppm for AQ)."""
    if config.secondary_column is not None and secondary_value is not None:
        return f"/ {int(secondary_value)}%"
    if config.unit == "ppm":
        return "ppm"
    return None


async def _get_latest_readings_batch(
    session: AsyncSession,
    sensors: list[Sensor],
) -> dict[str, tuple[float, float | None, datetime]]:
    """Get the latest reading for multiple sensors in minimal queries.

    Returns dict mapping sensor_id -> (value, secondary_value, timestamp).
    Groups sensors by type to minimize query count.
    """
    results: dict[str, tuple[float, float | None, datetime]] = {}

    # Group sensors by type
    sensors_by_type: dict[str, list[Sensor]] = {}
    for sensor in sensors:
        sensors_by_type.setdefault(sensor.sensor_type, []).append(sensor)

    for sensor_type, type_sensors in sensors_by_type.items():
        config = SENSOR_TYPE_REGISTRY.get(sensor_type)
        if not config:
            continue

        sensor_ids = [s.id for s in type_sensors]
        model = config.model

        # Use a window function to get the latest reading per sensor
        # This is a single query for all sensors of this type
        subq = (
            select(
                model.sensor_id,
                config.value_column.label("value"),
                model.timestamp,
                func.row_number()
                .over(partition_by=model.sensor_id, order_by=model.timestamp.desc())
                .label("rn"),
            )
            .where(model.sensor_id.in_(sensor_ids))
            .subquery()
        )

        if config.secondary_column is not None:
            # Need to join back to get secondary column
            result = await session.execute(
                select(
                    subq.c.sensor_id,
                    subq.c.value,
                    subq.c.timestamp,
                    config.secondary_column,
                )
                .select_from(subq)
                .join(
                    model,
                    (model.sensor_id == subq.c.sensor_id) & (model.timestamp == subq.c.timestamp),
                )
                .where(subq.c.rn == 1)
            )
            for row in result:
                results[row[0]] = (float(row[1]), float(row[3]), row[2])
        else:
            result = await session.execute(
                select(subq.c.sensor_id, subq.c.value, subq.c.timestamp).where(subq.c.rn == 1)
            )
            for row in result:
                value = float(row[1]) if not isinstance(row[1], bool) else float(row[1])
                results[row[0]] = (value, None, row[2])

    return results


async def _get_24h_trends_batch(
    session: AsyncSession,
    sensors: list[Sensor],
    end_times: dict[str, datetime],
) -> dict[str, list[float]]:
    """Get 24 hourly data points for multiple sensors using GROUP BY.

    Returns dict mapping sensor_id -> [24 hourly values].
    """
    results: dict[str, list[float]] = {s.id: [0.0] * TREND_HOURS for s in sensors}

    # Group sensors by type
    sensors_by_type: dict[str, list[Sensor]] = {}
    for sensor in sensors:
        sensors_by_type.setdefault(sensor.sensor_type, []).append(sensor)

    for sensor_type, type_sensors in sensors_by_type.items():
        config = SENSOR_TYPE_REGISTRY.get(sensor_type)
        if not config:
            continue

        sensor_ids = [s.id for s in type_sensors]
        model = config.model

        # Find the earliest start time needed (24h before the earliest end_time)
        min_end = min(end_times.get(sid, datetime.now()) for sid in sensor_ids)
        start_time = min_end - timedelta(hours=TREND_HOURS)

        # Single query with GROUP BY sensor_id and hour
        if config.supports_aggregation:
            # For numeric sensors: compute hourly averages
            query = (
                select(
                    model.sensor_id,
                    func.strftime("%Y-%m-%d %H", model.timestamp).label("hour_bucket"),
                    func.avg(config.value_column).label("avg_value"),
                )
                .where(model.sensor_id.in_(sensor_ids))
                .where(model.timestamp >= start_time)
                .group_by(model.sensor_id, func.strftime("%Y-%m-%d %H", model.timestamp))
            )
        else:
            # For boolean sensors: count events
            query = (
                select(
                    model.sensor_id,
                    func.strftime("%Y-%m-%d %H", model.timestamp).label("hour_bucket"),
                    func.sum(func.cast(config.value_column, Integer)).label("avg_value"),
                )
                .where(model.sensor_id.in_(sensor_ids))
                .where(model.timestamp >= start_time)
                .group_by(model.sensor_id, func.strftime("%Y-%m-%d %H", model.timestamp))
            )

        result = await session.execute(query)
        rows = result.all()

        # Build lookup: sensor_id -> {hour_bucket -> value}
        hourly_data: dict[str, dict[str, float]] = {sid: {} for sid in sensor_ids}
        for row in rows:
            sensor_id, hour_bucket, avg_value = row
            if avg_value is not None:
                hourly_data[sensor_id][hour_bucket] = float(avg_value)

        # Map hour buckets to trend array indices
        for sensor_id in sensor_ids:
            end_time = end_times.get(sensor_id, datetime.now())
            sensor_start = end_time - timedelta(hours=TREND_HOURS)
            trend = []

            for hour_offset in range(TREND_HOURS):
                hour_dt = sensor_start + timedelta(hours=hour_offset)
                bucket = hour_dt.strftime("%Y-%m-%d %H")
                value = hourly_data[sensor_id].get(bucket, 0.0)
                if config.supports_aggregation:
                    trend.append(round(value, 1))
                else:
                    trend.append(float(int(value)))

            results[sensor_id] = trend

    return results


async def _get_24h_stats_batch(
    session: AsyncSession,
    sensors: list[Sensor],
    end_times: dict[str, datetime],
) -> dict[str, SensorStats]:
    """Get 24-hour min/max/avg statistics for multiple sensors.

    Returns dict mapping sensor_id -> SensorStats.
    """
    results: dict[str, SensorStats] = {}

    # Group sensors by type
    sensors_by_type: dict[str, list[Sensor]] = {}
    for sensor in sensors:
        sensors_by_type.setdefault(sensor.sensor_type, []).append(sensor)

    for sensor_type, type_sensors in sensors_by_type.items():
        config = SENSOR_TYPE_REGISTRY.get(sensor_type)
        if not config:
            continue

        sensor_ids = [s.id for s in type_sensors]
        model = config.model

        if not config.supports_aggregation:
            # Door/motion don't have meaningful numeric stats
            for sid in sensor_ids:
                results[sid] = SensorStats(min=0, max=1, avg=0.5, unit="events")
            continue

        # Find time bounds
        min_end = min(end_times.get(sid, datetime.now()) for sid in sensor_ids)
        start_time = min_end - timedelta(hours=TREND_HOURS)

        # Single query for all sensors of this type
        query = (
            select(
                model.sensor_id,
                func.min(config.value_column),
                func.max(config.value_column),
                func.avg(config.value_column),
            )
            .where(model.sensor_id.in_(sensor_ids))
            .where(model.timestamp >= start_time)
            .group_by(model.sensor_id)
        )

        result = await session.execute(query)
        for row in result:
            sensor_id, min_val, max_val, avg_val = row
            precision = 1 if config.unit == "°C" else 0
            results[sensor_id] = SensorStats(
                min=round(min_val or 0, precision),
                max=round(max_val or 0, precision),
                avg=round(avg_val or 0, precision),
                unit=config.unit,
            )

        # Fill in any missing sensors with defaults
        for sid in sensor_ids:
            if sid not in results:
                results[sid] = SensorStats(min=0, max=0, avg=0, unit=config.unit)

    return results


def _build_sensor_config(
    sensor: Sensor,
    zone: Zone,
    latest: tuple[float, float | None, datetime],
    trend: list[float],
    stats: SensorStats,
) -> SensorConfig:
    """Build a complete SensorConfig for API response."""
    config = SENSOR_TYPE_REGISTRY.get(sensor.sensor_type)
    if not config:
        raise ValueError(f"Unknown sensor type: {sensor.sensor_type}")

    value, secondary_value, _ = latest

    # Compute status
    status, status_text = compute_status(
        value,
        sensor.warning_threshold,
        sensor.critical_threshold,
    )

    # Build raw_values for door sensors
    raw_values: dict[str, Any] | None = None
    if sensor.sensor_type == "door":
        raw_values = {"isOpen": bool(value)}

    # Build thresholds
    thresholds = None
    if sensor.warning_threshold is not None or sensor.critical_threshold is not None:
        thresholds = SensorThresholds(
            warning=sensor.warning_threshold,
            critical=sensor.critical_threshold,
        )

    return SensorConfig(
        id=sensor.id,
        sensor_type=sensor.sensor_type,
        zone=zone.name,
        label=sensor.label,
        reading=SensorReading(
            value=format_reading_value(config, value),
            unit=format_reading_unit(config, secondary_value),
            status=status,
            status_text=status_text,
            raw_values=raw_values,
        ),
        trend=trend,
        stats=stats,
        thresholds=thresholds,
    )


async def get_all_sensors(session: AsyncSession) -> list[SensorConfig]:
    """Get all sensors with computed current reading, 24h trend, and stats."""
    # Fetch all sensors with their zones in a single query
    result = await session.execute(select(Sensor, Zone).join(Zone, Sensor.zone_id == Zone.id))
    rows = result.all()

    if not rows:
        return []

    sensors = [row[0] for row in rows]
    zones_by_sensor = {row[0].id: row[1] for row in rows}

    # Batch fetch all data
    latest_readings = await _get_latest_readings_batch(session, sensors)

    # Filter to sensors that have readings
    sensors_with_readings = [s for s in sensors if s.id in latest_readings]
    if not sensors_with_readings:
        return []

    # Build end_times map from latest readings
    end_times = {sid: data[2] for sid, data in latest_readings.items()}

    # Batch fetch trends and stats
    trends = await _get_24h_trends_batch(session, sensors_with_readings, end_times)
    stats = await _get_24h_stats_batch(session, sensors_with_readings, end_times)

    # Build response
    sensor_configs = []
    for sensor in sensors_with_readings:
        latest = latest_readings[sensor.id]
        zone = zones_by_sensor[sensor.id]
        sensor_configs.append(
            _build_sensor_config(
                sensor,
                zone,
                latest,
                trends.get(sensor.id, [0.0] * TREND_HOURS),
                stats.get(sensor.id, SensorStats(min=0, max=0, avg=0, unit="")),
            )
        )

    return sensor_configs


async def get_sensor_by_id(session: AsyncSession, sensor_id: str) -> SensorConfig | None:
    """Get a single sensor with computed data."""
    result = await session.execute(
        select(Sensor, Zone).join(Zone, Sensor.zone_id == Zone.id).where(Sensor.id == sensor_id)
    )
    row = result.one_or_none()
    if not row:
        return None

    sensor, zone = row
    sensors = [sensor]

    # Fetch data for this single sensor
    latest_readings = await _get_latest_readings_batch(session, sensors)
    if sensor.id not in latest_readings:
        return None

    end_times = {sensor.id: latest_readings[sensor.id][2]}
    trends = await _get_24h_trends_batch(session, sensors, end_times)
    stats = await _get_24h_stats_batch(session, sensors, end_times)

    return _build_sensor_config(
        sensor,
        zone,
        latest_readings[sensor.id],
        trends.get(sensor.id, [0.0] * TREND_HOURS),
        stats.get(sensor.id, SensorStats(min=0, max=0, avg=0, unit="")),
    )


async def get_sensors_by_zone(
    session: AsyncSession,
    zone_id: str,
    sensor_type: str | None = None,
) -> list[SensorConfig]:
    """Get all sensors in a specific zone, optionally filtered by type."""
    query = (
        select(Sensor, Zone).join(Zone, Sensor.zone_id == Zone.id).where(Sensor.zone_id == zone_id)
    )
    if sensor_type:
        query = query.where(Sensor.sensor_type == sensor_type)

    result = await session.execute(query)
    rows = result.all()

    if not rows:
        return []

    sensors = [row[0] for row in rows]
    zones_by_sensor = {row[0].id: row[1] for row in rows}

    # Batch fetch all data
    latest_readings = await _get_latest_readings_batch(session, sensors)

    sensors_with_readings = [s for s in sensors if s.id in latest_readings]
    if not sensors_with_readings:
        return []

    end_times = {sid: data[2] for sid, data in latest_readings.items()}
    trends = await _get_24h_trends_batch(session, sensors_with_readings, end_times)
    stats = await _get_24h_stats_batch(session, sensors_with_readings, end_times)

    sensor_configs = []
    for sensor in sensors_with_readings:
        latest = latest_readings[sensor.id]
        zone = zones_by_sensor[sensor.id]
        sensor_configs.append(
            _build_sensor_config(
                sensor,
                zone,
                latest,
                trends.get(sensor.id, [0.0] * TREND_HOURS),
                stats.get(sensor.id, SensorStats(min=0, max=0, avg=0, unit="")),
            )
        )

    return sensor_configs
