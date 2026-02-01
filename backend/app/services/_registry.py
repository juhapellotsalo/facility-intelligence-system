"""Sensor type registry for eliminating repetitive if/elif branching."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import InstrumentedAttribute

from app.models import AirQualityReading, DoorReading, EnvironmentalReading, MotionReading


@dataclass(frozen=True)
class SensorTypeConfig:
    """Configuration for a sensor type's reading model and value extraction."""

    model: type
    value_column: InstrumentedAttribute[Any]
    unit: str
    # For sensors that have a secondary value (e.g., humidity for environmental)
    secondary_column: InstrumentedAttribute[Any] | None = None
    secondary_unit: str | None = None
    # For boolean sensors, how to format the value
    format_value: Callable[[float], str] | None = None
    # Whether this sensor type supports numeric aggregations (avg/min/max)
    supports_aggregation: bool = True


def _format_door(value: float) -> str:
    return "Open" if value else "Closed"


def _format_motion(value: float) -> str:
    return "Motion detected" if value else "No motion"


SENSOR_TYPE_REGISTRY: dict[str, SensorTypeConfig] = {
    "environmental": SensorTypeConfig(
        model=EnvironmentalReading,
        value_column=EnvironmentalReading.temperature,
        unit="°C",
        secondary_column=EnvironmentalReading.humidity,
        secondary_unit="%",
    ),
    "air_quality": SensorTypeConfig(
        model=AirQualityReading,
        value_column=AirQualityReading.co2_ppm,
        unit="ppm",
    ),
    "door": SensorTypeConfig(
        model=DoorReading,
        value_column=DoorReading.is_open,
        unit="events",
        format_value=_format_door,
        supports_aggregation=False,
    ),
    "motion": SensorTypeConfig(
        model=MotionReading,
        value_column=MotionReading.motion_detected,
        unit="events",
        format_value=_format_motion,
        supports_aggregation=False,
    ),
}


def get_sensor_config(sensor_type: str) -> SensorTypeConfig | None:
    """Get configuration for a sensor type."""
    return SENSOR_TYPE_REGISTRY.get(sensor_type)
