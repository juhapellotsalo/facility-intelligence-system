"""Event API routes for door and presence events."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.events import DoorEventsResponse, PresenceEventsResponse
from app.services.event_service import get_door_events, get_presence_events

# Maximum time range and result limits
MAX_EVENTS_DAYS = 7
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/doors/events", response_model=DoorEventsResponse)
async def list_door_events(
    sensor_id: str | None = Query(None, description="Filter by specific door sensor"),
    zone_id: str | None = Query(None, description="Filter by zone"),
    start: datetime | None = Query(None, description="Start of time range (ISO format)"),
    end: datetime | None = Query(None, description="End of time range (ISO format)"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Max events to return"),
    session: AsyncSession = Depends(get_db),
) -> DoorEventsResponse:
    """Get door open/close events with computed durations."""
    # Default to last 24 hours if not specified
    now = datetime.now(UTC).replace(tzinfo=None)  # Use naive UTC for SQLite
    if end is None:
        end = now
    if start is None:
        start = end - timedelta(hours=24)

    # Validate time range
    if start >= end:
        raise HTTPException(status_code=400, detail="start must be before end")

    # Enforce maximum time range
    max_range = timedelta(days=MAX_EVENTS_DAYS)
    if end - start > max_range:
        raise HTTPException(
            status_code=400,
            detail=f"Time range cannot exceed {MAX_EVENTS_DAYS} days",
        )

    events = await get_door_events(
        session,
        start=start,
        end=end,
        sensor_id=sensor_id,
        zone_id=zone_id,
    )

    # Apply limit
    limited_events = events[:limit]

    return DoorEventsResponse(
        events=limited_events,
        total_count=len(events),
    )


@router.get("/presence/events", response_model=PresenceEventsResponse)
async def list_presence_events(
    sensor_id: str | None = Query(None, description="Filter by specific motion sensor"),
    zone_id: str | None = Query(None, description="Filter by zone"),
    start: datetime | None = Query(None, description="Start of time range (ISO format)"),
    end: datetime | None = Query(None, description="End of time range (ISO format)"),
    min_duration: int = Query(0, ge=0, description="Minimum duration in seconds"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Max events to return"),
    session: AsyncSession = Depends(get_db),
) -> PresenceEventsResponse:
    """Get presence events with safety concern flags."""
    # Default to last 24 hours if not specified
    now = datetime.now(UTC).replace(tzinfo=None)  # Use naive UTC for SQLite
    if end is None:
        end = now
    if start is None:
        start = end - timedelta(hours=24)

    # Validate time range
    if start >= end:
        raise HTTPException(status_code=400, detail="start must be before end")

    # Enforce maximum time range
    max_range = timedelta(days=MAX_EVENTS_DAYS)
    if end - start > max_range:
        raise HTTPException(
            status_code=400,
            detail=f"Time range cannot exceed {MAX_EVENTS_DAYS} days",
        )

    events = await get_presence_events(
        session,
        start=start,
        end=end,
        sensor_id=sensor_id,
        zone_id=zone_id,
        min_duration_seconds=min_duration,
    )

    safety_concerns = sum(1 for e in events if e.is_safety_concern)

    # Apply limit
    limited_events = events[:limit]

    return PresenceEventsResponse(
        events=limited_events,
        total_count=len(events),
        safety_concerns_count=safety_concerns,
    )
