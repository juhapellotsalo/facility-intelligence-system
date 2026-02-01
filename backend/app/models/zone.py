"""Zone model."""

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Zone(Base):
    """Facility zone (Loading Bay, Cold Room A, etc.)."""

    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_temp_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_temp_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationship to sensors
    sensors: Mapped[list["Sensor"]] = relationship(back_populates="zone")


# Import here to avoid circular imports
from app.models.sensor import Sensor  # noqa: E402, F401
