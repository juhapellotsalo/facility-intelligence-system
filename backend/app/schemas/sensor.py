"""Pydantic schemas matching frontend TypeScript interfaces."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SensorThresholds(BaseModel):
    """Warning and critical thresholds for a sensor."""

    warning: float | None = None
    critical: float | None = None


class SensorStats(BaseModel):
    """24-hour statistics for a sensor."""

    min: float
    max: float
    avg: float
    unit: str


class SensorReading(BaseModel):
    """Current sensor reading with status."""

    model_config = ConfigDict(populate_by_name=True)

    value: str  # Formatted string, e.g., "-14.2°C"
    unit: str | None = None  # Optional suffix, e.g., "/ 68%"
    status: Literal["normal", "warning", "critical"]
    status_text: str = Field(serialization_alias="statusText")
    raw_values: dict[str, float | str | bool] | None = Field(
        default=None, serialization_alias="rawValues"
    )


class SensorConfig(BaseModel):
    """Complete sensor configuration matching frontend SensorConfig interface."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    sensor_type: Literal["environmental", "air_quality", "thermal_presence", "door", "motion"] = (
        Field(serialization_alias="sensorType")
    )
    zone: str  # Zone display name, e.g., "Cold Room B — Frozen"
    label: str
    reading: SensorReading
    trend: list[float]  # 24 hourly data points
    stats: SensorStats
    thresholds: SensorThresholds | None = None
