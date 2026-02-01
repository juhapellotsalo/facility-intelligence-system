"""Event service layer — computes door events and presence windows from raw readings."""

from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DoorReading, MotionReading, Sensor
from app.schemas.events import DoorEvent, PresenceEvent

__all__ = ["get_door_events", "get_presence_events"]

# Safety concern threshold: 10 minutes in a cold room
SAFETY_CONCERN_THRESHOLD_SECONDS = 600


async def get_door_events(
    session: AsyncSession,
    start: datetime,
    end: datetime,
    sensor_id: str | None = None,
    zone_id: str | None = None,
) -> list[DoorEvent]:
    """
    Compute door open/close events from raw door readings.

    Events are computed by finding state transitions:
    - An "open" event starts when is_open transitions from False to True
    - An "open" event ends when is_open transitions from True to False
    - Duration is calculated between open and close timestamps
    """
    # Build query for door sensors
    query = select(DoorReading).where(
        and_(
            DoorReading.timestamp >= start,
            DoorReading.timestamp <= end,
        )
    )

    if sensor_id:
        query = query.where(DoorReading.sensor_id == sensor_id)
    elif zone_id:
        # Filter by zone through sensor table
        sensor_ids = await _get_sensor_ids_for_zone(session, zone_id, "door")
        query = query.where(DoorReading.sensor_id.in_(sensor_ids))

    query = query.order_by(DoorReading.sensor_id, DoorReading.timestamp)

    result = await session.execute(query)
    readings = result.scalars().all()

    # Group by sensor and compute events
    events: list[DoorEvent] = []
    current_sensor_id: str | None = None
    current_event_start: datetime | None = None
    prev_is_open: bool | None = None

    for reading in readings:
        # Reset state when switching sensors
        if reading.sensor_id != current_sensor_id:
            # Close any open event from previous sensor
            if current_event_start is not None and current_sensor_id is not None:
                events.append(
                    DoorEvent(
                        sensor_id=current_sensor_id,
                        opened_at=current_event_start,
                        closed_at=None,  # Still open at end of query
                        duration_seconds=int((end - current_event_start).total_seconds()),
                    )
                )
            current_sensor_id = reading.sensor_id
            current_event_start = None
            prev_is_open = None

        # Detect transitions
        if prev_is_open is not None:
            # Transition from closed to open: start new event
            if not prev_is_open and reading.is_open:
                current_event_start = reading.timestamp
            # Transition from open to closed: close event
            elif prev_is_open and not reading.is_open and current_event_start is not None:
                events.append(
                    DoorEvent(
                        sensor_id=reading.sensor_id,
                        opened_at=current_event_start,
                        closed_at=reading.timestamp,
                        duration_seconds=int(
                            (reading.timestamp - current_event_start).total_seconds()
                        ),
                    )
                )
                current_event_start = None
        else:
            # First reading for this sensor - if open, start an event
            if reading.is_open:
                current_event_start = reading.timestamp

        prev_is_open = reading.is_open

    # Handle any still-open event at end
    if current_event_start is not None and current_sensor_id is not None:
        events.append(
            DoorEvent(
                sensor_id=current_sensor_id,
                opened_at=current_event_start,
                closed_at=None,
                duration_seconds=int((end - current_event_start).total_seconds()),
            )
        )

    return events


async def get_presence_events(
    session: AsyncSession,
    start: datetime,
    end: datetime,
    sensor_id: str | None = None,
    zone_id: str | None = None,
    min_duration_seconds: int = 0,
) -> list[PresenceEvent]:
    """
    Compute presence windows from motion readings.

    A presence event is a continuous period of motion detection.
    Events are flagged as safety concerns if duration exceeds threshold (10 min).

    Motion readings at 15-min intervals mean presence windows are approximate:
    - Start = first motion detected
    - End = timestamp of first reading with no motion after continuous motion
    """
    # Build query for motion sensors
    query = (
        select(MotionReading, Sensor.zone_id)
        .join(Sensor, MotionReading.sensor_id == Sensor.id)
        .where(
            and_(
                MotionReading.timestamp >= start,
                MotionReading.timestamp <= end,
            )
        )
    )

    if sensor_id:
        query = query.where(MotionReading.sensor_id == sensor_id)
    elif zone_id:
        query = query.where(Sensor.zone_id == zone_id)

    query = query.order_by(MotionReading.sensor_id, MotionReading.timestamp)

    result = await session.execute(query)
    rows = result.all()

    # Group by sensor and compute events
    events: list[PresenceEvent] = []
    current_sensor_id: str | None = None
    current_zone_id: str | None = None
    current_event_start: datetime | None = None
    prev_motion: bool | None = None

    for reading, zone in rows:
        # Reset state when switching sensors
        if reading.sensor_id != current_sensor_id:
            # Close any open event from previous sensor
            if current_event_start is not None and current_sensor_id is not None:
                duration = int((end - current_event_start).total_seconds())
                if duration >= min_duration_seconds:
                    events.append(
                        PresenceEvent(
                            sensor_id=current_sensor_id,
                            zone_id=current_zone_id or "",
                            started_at=current_event_start,
                            ended_at=None,
                            duration_seconds=duration,
                            is_safety_concern=duration >= SAFETY_CONCERN_THRESHOLD_SECONDS,
                        )
                    )
            current_sensor_id = reading.sensor_id
            current_zone_id = zone
            current_event_start = None
            prev_motion = None

        # Detect transitions
        if prev_motion is not None:
            # Transition from no motion to motion: start new event
            if not prev_motion and reading.motion_detected:
                current_event_start = reading.timestamp
            # Transition from motion to no motion: close event
            elif prev_motion and not reading.motion_detected and current_event_start is not None:
                duration = int((reading.timestamp - current_event_start).total_seconds())
                if duration >= min_duration_seconds:
                    events.append(
                        PresenceEvent(
                            sensor_id=reading.sensor_id,
                            zone_id=zone,
                            started_at=current_event_start,
                            ended_at=reading.timestamp,
                            duration_seconds=duration,
                            is_safety_concern=duration >= SAFETY_CONCERN_THRESHOLD_SECONDS,
                        )
                    )
                current_event_start = None
        else:
            # First reading for this sensor - if motion, start an event
            if reading.motion_detected:
                current_event_start = reading.timestamp

        prev_motion = reading.motion_detected

    # Handle any still-active event at end
    if current_event_start is not None and current_sensor_id is not None:
        duration = int((end - current_event_start).total_seconds())
        if duration >= min_duration_seconds:
            events.append(
                PresenceEvent(
                    sensor_id=current_sensor_id,
                    zone_id=current_zone_id or "",
                    started_at=current_event_start,
                    ended_at=None,
                    duration_seconds=duration,
                    is_safety_concern=duration >= SAFETY_CONCERN_THRESHOLD_SECONDS,
                )
            )

    return events


async def _get_sensor_ids_for_zone(
    session: AsyncSession,
    zone_id: str,
    sensor_type: str,
) -> list[str]:
    """Get sensor IDs for a given zone and sensor type."""
    result = await session.execute(
        select(Sensor.id).where(
            and_(
                Sensor.zone_id == zone_id,
                Sensor.sensor_type == sensor_type,
            )
        )
    )
    return [row[0] for row in result.all()]
