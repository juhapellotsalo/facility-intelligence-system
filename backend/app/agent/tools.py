"""Agent tools for querying facility data.

Contains:
- Pydantic input schemas for each tool
- Tool implementations using @tool decorator
- Helper functions for data formatting
"""

from datetime import datetime
from typing import TypedDict

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.database import get_session
from app.services import (
    get_door_events as service_get_door_events,
)
from app.services import (
    get_presence_events,
    get_sensor_baseline,
    get_sensor_readings,
    get_sensors_by_zone,
)

# --- Tool Result Type ---


class ToolResult(TypedDict):
    """Standard return type for all agent tools."""

    data: list | dict
    summary: str


# --- Input Schemas ---


class QuerySensorDataInput(BaseModel):
    """Input schema for query_sensor_data tool."""

    sensor_id: str | None = Field(
        None, description="Specific sensor ID to query (e.g., 'cold-a-temp')"
    )
    zone_id: str | None = Field(
        None, description="Zone ID to query all sensors in (e.g., 'Z3' for Cold Room B)"
    )
    sensor_type: str | None = Field(
        None,
        description="Filter by sensor type: 'environmental', 'air_quality', 'door', 'motion'",
    )
    start: str = Field(..., description="Start time in ISO format (e.g., '2026-01-29T00:00:00')")
    end: str = Field(..., description="End time in ISO format (e.g., '2026-01-29T23:59:59')")
    aggregation: str = Field(
        "raw",
        description="Aggregation interval: 'raw' (native resolution), '1h' (hourly), '1d' (daily)",
    )


class GetDoorEventsInput(BaseModel):
    """Input schema for get_door_events tool."""

    sensor_id: str | None = Field(None, description="Specific door sensor ID to query")
    zone_id: str | None = Field(None, description="Zone ID to get door events for")
    start: str = Field(..., description="Start time in ISO format")
    end: str = Field(..., description="End time in ISO format")


class GetThermalPresenceInput(BaseModel):
    """Input schema for get_thermal_presence tool."""

    sensor_id: str | None = Field(None, description="Specific presence sensor ID to query")
    zone_id: str | None = Field(None, description="Zone ID to get presence events for")
    start: str = Field(..., description="Start time in ISO format")
    end: str = Field(..., description="End time in ISO format")
    min_duration: int = Field(
        0, description="Minimum duration in seconds to include (0 = all events)"
    )


class GetBaselinesInput(BaseModel):
    """Input schema for get_baselines tool."""

    sensor_id: str = Field(..., description="Sensor ID to get baseline statistics for")
    hours: int = Field(24, description="Number of hours to compute baseline from (default 24)")


# --- Helper Functions ---


def _parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string."""
    # Handle Z suffix (UTC timezone indicator)
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1]

    # Handle timezone offset (e.g., +00:00)
    if "+" in dt_str and dt_str.index("+") > 10:
        dt_str = dt_str.split("+")[0]
    elif dt_str.count("-") > 2:
        # Handle negative timezone offset
        parts = dt_str.rsplit("-", 1)
        if len(parts[1]) <= 5:  # Likely timezone, not date part
            dt_str = parts[0]

    # Handle various ISO formats
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {dt_str}")


def _format_duration(seconds: int) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes:
            return f"{hours} hour{'s' if hours != 1 else ''} {minutes} min"
        return f"{hours} hour{'s' if hours != 1 else ''}"


# --- Tool Implementations ---


@tool(args_schema=QuerySensorDataInput)
async def query_sensor_data(
    sensor_id: str | None = None,
    zone_id: str | None = None,
    sensor_type: str | None = None,
    start: str = "",
    end: str = "",
    aggregation: str = "raw",
) -> ToolResult:
    """Query historical sensor readings for a specific sensor or zone.

    Use this tool to get temperature, humidity, air quality, or other sensor
    readings over a time period. Returns timestamped data points.
    """
    if not sensor_id and not zone_id:
        return {
            "data": [],
            "summary": "Error: Please specify either sensor_id or zone_id to query.",
        }

    try:
        start_dt = _parse_datetime(start)
        end_dt = _parse_datetime(end)
    except ValueError as e:
        return {"data": [], "summary": f"Error parsing dates: {e}"}

    # Map aggregation to interval
    interval_map = {
        "raw": "raw",
        "hourly": "1h",
        "1h": "1h",
        "daily": "1d",
        "1d": "1d",
    }
    interval = interval_map.get(aggregation, "raw")

    async with get_session() as session:
        if sensor_id:
            # Query single sensor
            result = await get_sensor_readings(session, sensor_id, start_dt, end_dt, interval)
            if not result:
                return {
                    "data": [],
                    "summary": f"No sensor found with ID {sensor_id}.",
                }

            readings = [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "value": r.value,
                    "humidity": r.humidity,
                }
                for r in result.readings
            ]

            if not readings:
                return {
                    "data": [],
                    "summary": (
                        f"No readings found for sensor {sensor_id} in the specified time range."
                    ),
                }

            # Compute summary stats
            values = [r["value"] for r in readings]
            min_val = min(values)
            max_val = max(values)

            # Determine unit based on sensor type
            unit = (
                "°C"
                if result.sensor_type == "environmental"
                else "ppm"
                if result.sensor_type == "air_quality"
                else ""
            )

            return {
                "data": readings,
                "summary": f"Found {len(readings)} readings for sensor {sensor_id}. "
                f"Value range: {min_val}{unit} to {max_val}{unit}.",
            }

        # Query all sensors in zone
        sensors = await get_sensors_by_zone(session, zone_id, sensor_type)
        if not sensors:
            return {
                "data": [],
                "summary": f"No sensors found in zone {zone_id}"
                + (f" with type '{sensor_type}'" if sensor_type else "")
                + ".",
            }

        # Collect readings from all sensors in the zone
        all_readings = []
        sensor_summaries = []

        for sensor in sensors:
            result = await get_sensor_readings(session, str(sensor.id), start_dt, end_dt, interval)
            if result and result.readings:
                sensor_readings = [
                    {
                        "sensor_id": sensor.id,
                        "sensor_name": sensor.label,
                        "timestamp": r.timestamp.isoformat(),
                        "value": r.value,
                        "humidity": r.humidity,
                    }
                    for r in result.readings
                ]
                all_readings.extend(sensor_readings)

                values = [r.value for r in result.readings]
                unit = (
                    "°C"
                    if result.sensor_type == "environmental"
                    else "ppm"
                    if result.sensor_type == "air_quality"
                    else ""
                )
                sensor_summaries.append(
                    f"{sensor.label}: {min(values)}{unit} to {max(values)}{unit}"
                )

        if not all_readings:
            return {
                "data": [],
                "summary": (
                    f"No readings found for sensors in zone {zone_id} in the specified time range."
                ),
            }

        summary = (
            f"Found {len(all_readings)} readings from "
            f"{len(sensor_summaries)} sensors in zone {zone_id}. "
        )
        if len(sensor_summaries) <= 3:
            summary += " | ".join(sensor_summaries)
        else:
            summary += f"Sensors: {', '.join(s.name for s in sensors[:5])}"
            if len(sensors) > 5:
                summary += f" and {len(sensors) - 5} more"

        return {"data": all_readings, "summary": summary}


@tool(args_schema=GetDoorEventsInput)
async def get_door_events(
    sensor_id: str | None = None,
    zone_id: str | None = None,
    start: str = "",
    end: str = "",
) -> ToolResult:
    """Get door open/close events with durations.

    Use this to see when doors were opened, how long they stayed open,
    and identify patterns in door activity.
    """
    try:
        start_dt = _parse_datetime(start)
        end_dt = _parse_datetime(end)
    except ValueError as e:
        return {"data": [], "summary": f"Error parsing dates: {e}"}

    async with get_session() as session:
        events = await service_get_door_events(
            session, start_dt, end_dt, sensor_id=sensor_id, zone_id=zone_id
        )

        if not events:
            return {
                "data": [],
                "summary": "No door events found in the specified time range.",
            }

        # Convert to serializable format
        event_data = [
            {
                "sensor_id": e.sensor_id,
                "opened_at": e.opened_at.isoformat(),
                "closed_at": e.closed_at.isoformat() if e.closed_at else None,
                "duration_seconds": e.duration_seconds,
            }
            for e in events
        ]

        # Find longest duration
        longest = max(events, key=lambda e: e.duration_seconds)
        longest_duration = _format_duration(longest.duration_seconds)

        return {
            "data": event_data,
            "summary": f"{len(events)} door event{'s' if len(events) != 1 else ''} found. "
            f"Longest open: {longest_duration}.",
        }


@tool(args_schema=GetThermalPresenceInput)
async def get_thermal_presence(
    sensor_id: str | None = None,
    zone_id: str | None = None,
    start: str = "",
    end: str = "",
    min_duration: int = 0,
) -> ToolResult:
    """Get motion sensor events showing when motion was detected.

    Use this for any motion sensor query (loading-motion, cold-a-motion, cold-b-motion).
    Returns periods of detected motion. Events over 10 minutes in freezer zones
    are flagged as safety concerns for worker monitoring.
    """
    try:
        start_dt = _parse_datetime(start)
        end_dt = _parse_datetime(end)
    except ValueError as e:
        return {"data": [], "summary": f"Error parsing dates: {e}"}

    async with get_session() as session:
        events = await get_presence_events(
            session,
            start_dt,
            end_dt,
            sensor_id=sensor_id,
            zone_id=zone_id,
            min_duration_seconds=min_duration,
        )

        if not events:
            return {
                "data": [],
                "summary": "No presence events found in the specified time range.",
            }

        # Convert to serializable format
        event_data = [
            {
                "sensor_id": e.sensor_id,
                "zone_id": e.zone_id,
                "started_at": e.started_at.isoformat(),
                "ended_at": e.ended_at.isoformat() if e.ended_at else None,
                "duration_seconds": e.duration_seconds,
                "is_safety_concern": e.is_safety_concern,
            }
            for e in events
        ]

        # Count safety concerns
        safety_concerns = sum(1 for e in events if e.is_safety_concern)

        count = len(events)
        summary = f"{count} presence event{'s' if count != 1 else ''} found."
        if safety_concerns:
            concern_word = "concern" if safety_concerns == 1 else "concerns"
            summary += f" {safety_concerns} safety {concern_word} (>10 min in cold zone)."

        return {"data": event_data, "summary": summary}


@tool(args_schema=GetBaselinesInput)
async def get_baselines(
    sensor_id: str = "",
    hours: int = 24,
) -> ToolResult:
    """Get baseline statistics for a sensor to understand normal operating patterns.

    Returns mean, standard deviation, min, and max values computed from
    historical readings. Useful for detecting anomalies.
    """
    if not sensor_id:
        return {
            "data": {},
            "summary": "Error: sensor_id is required.",
        }

    async with get_session() as session:
        baseline = await get_sensor_baseline(session, sensor_id, hours)

        if not baseline:
            return {
                "data": {},
                "summary": f"No baseline data found for sensor {sensor_id}. "
                "The sensor may not exist or have no recent readings.",
            }

        data = {
            "sensor_id": baseline.sensor_id,
            "mean": baseline.mean,
            "std_dev": baseline.std_dev,
            "min": baseline.min,
            "max": baseline.max,
            "unit": baseline.unit,
            "sample_count": baseline.sample_count,
            "period_hours": baseline.period_hours,
        }

        summary = (
            f"Sensor {sensor_id} baseline ({hours}h): "
            f"{baseline.mean}{baseline.unit} ± {baseline.std_dev}{baseline.unit} "
            f"(range: {baseline.min} to {baseline.max}{baseline.unit}, "
            f"{baseline.sample_count} samples)."
        )

        return {"data": data, "summary": summary}


# --- Tool Collection ---


def get_all_tools() -> list:
    """Return all available tools for the agent."""
    return [
        query_sensor_data,
        get_door_events,
        get_thermal_presence,
        get_baselines,
    ]
