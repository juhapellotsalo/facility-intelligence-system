"""Sensor reading models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EnvironmentalReading(Base):
    """Temperature and humidity readings from environmental sensors."""

    __tablename__ = "environmental_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[str] = mapped_column(String(50), ForeignKey("sensors.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (Index("ix_environmental_sensor_time", "sensor_id", "timestamp"),)


class AirQualityReading(Base):
    """CO2 and air quality readings."""

    __tablename__ = "air_quality_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[str] = mapped_column(String(50), ForeignKey("sensors.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    co2_ppm: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (Index("ix_airquality_sensor_time", "sensor_id", "timestamp"),)


class DoorReading(Base):
    """Door open/closed state readings."""

    __tablename__ = "door_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[str] = mapped_column(String(50), ForeignKey("sensors.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (Index("ix_door_sensor_time", "sensor_id", "timestamp"),)


class MotionReading(Base):
    """Motion detection readings."""

    __tablename__ = "motion_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[str] = mapped_column(String(50), ForeignKey("sensors.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    motion_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (Index("ix_motion_sensor_time", "sensor_id", "timestamp"),)
