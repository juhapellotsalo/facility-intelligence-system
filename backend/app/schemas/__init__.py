"""Pydantic schemas for API request/response models."""

from app.schemas.events import (
    DoorEvent,
    DoorEventsResponse,
    HourlyBaseline,
    PresenceEvent,
    PresenceEventsResponse,
    ReadingPoint,
    ReadingsResponse,
    SensorBaseline,
)
from app.schemas.sensor import (
    SensorConfig,
    SensorReading,
    SensorStats,
    SensorThresholds,
)

__all__ = [
    # Sensor schemas
    "SensorConfig",
    "SensorReading",
    "SensorStats",
    "SensorThresholds",
    # Event schemas
    "DoorEvent",
    "DoorEventsResponse",
    "PresenceEvent",
    "PresenceEventsResponse",
    "ReadingPoint",
    "ReadingsResponse",
    "SensorBaseline",
    "HourlyBaseline",
]
