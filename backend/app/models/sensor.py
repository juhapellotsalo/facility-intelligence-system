"""Sensor model."""

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Sensor(Base):
    """Sensor device in the facility."""

    __tablename__ = "sensors"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    zone_id: Mapped[str] = mapped_column(String(50), ForeignKey("zones.id"), nullable=False)
    sensor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    warning_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    critical_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationship to zone
    zone: Mapped["Zone"] = relationship(back_populates="sensors")


# Import here to avoid circular imports
from app.models.zone import Zone  # noqa: E402, F401
