"""Pydantic schemas for events, readings, and baselines."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# --- Reading Schemas ---


class ReadingPoint(BaseModel):
    """A single timestamped reading."""

    model_config = ConfigDict(populate_by_name=True)

    timestamp: datetime
    value: float
    humidity: float | None = None  # Only for environmental sensors


class ReadingsResponse(BaseModel):
    """Response for historical readings query."""

    model_config = ConfigDict(populate_by_name=True)

    sensor_id: str = Field(serialization_alias="sensorId")
    sensor_type: str = Field(serialization_alias="sensorType")
    interval: str  # "raw", "1h", "1d"
    readings: list[ReadingPoint]


# --- Door Event Schemas ---


class DoorEvent(BaseModel):
    """A computed door open/close event with duration."""

    model_config = ConfigDict(populate_by_name=True)

    sensor_id: str = Field(serialization_alias="sensorId")
    opened_at: datetime = Field(serialization_alias="openedAt")
    closed_at: datetime | None = Field(serialization_alias="closedAt")
    duration_seconds: int = Field(serialization_alias="durationSeconds")


class DoorEventsResponse(BaseModel):
    """Response for door events query."""

    model_config = ConfigDict(populate_by_name=True)

    events: list[DoorEvent]
    total_count: int = Field(serialization_alias="totalCount")


# --- Presence Event Schemas ---


class PresenceEvent(BaseModel):
    """A computed presence event (continuous motion detection window)."""

    model_config = ConfigDict(populate_by_name=True)

    sensor_id: str = Field(serialization_alias="sensorId")
    zone_id: str = Field(serialization_alias="zoneId")
    started_at: datetime = Field(serialization_alias="startedAt")
    ended_at: datetime | None = Field(serialization_alias="endedAt")
    duration_seconds: int = Field(serialization_alias="durationSeconds")
    is_safety_concern: bool = Field(serialization_alias="isSafetyConcern")


class PresenceEventsResponse(BaseModel):
    """Response for presence events query."""

    model_config = ConfigDict(populate_by_name=True)

    events: list[PresenceEvent]
    total_count: int = Field(serialization_alias="totalCount")
    safety_concerns_count: int = Field(serialization_alias="safetyConcernsCount")


# --- Baseline Schemas ---


class SensorBaseline(BaseModel):
    """Baseline statistics for a sensor."""

    model_config = ConfigDict(populate_by_name=True)

    sensor_id: str = Field(serialization_alias="sensorId")
    mean: float
    std_dev: float = Field(serialization_alias="stdDev")
    min: float
    max: float
    unit: str
    sample_count: int = Field(serialization_alias="sampleCount")
    period_hours: int = Field(serialization_alias="periodHours")


class HourlyBaseline(BaseModel):
    """Per-hour-of-day baseline (for time-of-day patterns)."""

    model_config = ConfigDict(populate_by_name=True)

    hour: int  # 0-23
    mean: float
    std_dev: float = Field(serialization_alias="stdDev")
    sample_count: int = Field(serialization_alias="sampleCount")
