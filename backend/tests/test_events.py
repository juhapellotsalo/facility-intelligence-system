"""Tests for event and readings API endpoints."""

from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# --- Readings endpoint tests ---


@pytest.mark.asyncio
async def test_get_sensor_readings_response_structure(client: AsyncClient):
    """Test readings endpoint returns correct structure."""
    response = await client.get("/api/sensors/cold-b-temp/readings")
    assert response.status_code == 200

    data = response.json()
    assert "sensorId" in data
    assert "sensorType" in data
    assert "interval" in data
    assert "readings" in data
    assert isinstance(data["readings"], list)


@pytest.mark.asyncio
async def test_get_sensor_readings_with_time_range(client: AsyncClient):
    """Test fetching readings with custom time range."""
    end = datetime.now()
    start = end - timedelta(hours=6)

    response = await client.get(
        "/api/sensors/cold-b-temp/readings",
        params={
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert "readings" in data
    assert isinstance(data["readings"], list)


@pytest.mark.asyncio
async def test_get_sensor_readings_interval_param(client: AsyncClient):
    """Test fetching readings with interval aggregation."""
    response = await client.get(
        "/api/sensors/cold-b-temp/readings",
        params={"interval": "1h"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["interval"] == "1h"


@pytest.mark.asyncio
async def test_get_sensor_readings_not_found(client: AsyncClient):
    """Test 404 for unknown sensor readings."""
    response = await client.get("/api/sensors/unknown-sensor-xyz/readings")
    assert response.status_code == 404


# --- Baseline endpoint tests ---


@pytest.mark.asyncio
async def test_get_sensor_baseline_not_found(client: AsyncClient):
    """Test 404 for unknown sensor baseline."""
    response = await client.get("/api/sensors/unknown-sensor-xyz/baseline")
    assert response.status_code == 404


# --- Door events endpoint tests ---


@pytest.mark.asyncio
async def test_list_door_events_response_structure(client: AsyncClient):
    """Test door events endpoint returns correct structure."""
    response = await client.get("/api/doors/events")
    assert response.status_code == 200

    data = response.json()
    assert "events" in data
    assert "totalCount" in data
    assert isinstance(data["events"], list)
    assert isinstance(data["totalCount"], int)


@pytest.mark.asyncio
async def test_list_door_events_by_sensor(client: AsyncClient):
    """Test filtering door events by sensor."""
    response = await client.get(
        "/api/doors/events",
        params={"sensor_id": "loading-door"},
    )
    assert response.status_code == 200

    data = response.json()
    # All events should be for the specified sensor
    for event in data["events"]:
        assert event["sensorId"] == "loading-door"


@pytest.mark.asyncio
async def test_door_events_time_range_params(client: AsyncClient):
    """Test door events endpoint accepts time range params."""
    end = datetime.now()
    start = end - timedelta(hours=48)

    response = await client.get(
        "/api/doors/events",
        params={
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    )
    assert response.status_code == 200


# --- Presence events endpoint tests ---


@pytest.mark.asyncio
async def test_list_presence_events_response_structure(client: AsyncClient):
    """Test presence events endpoint returns correct structure."""
    response = await client.get("/api/presence/events")
    assert response.status_code == 200

    data = response.json()
    assert "events" in data
    assert "totalCount" in data
    assert "safetyConcernsCount" in data
    assert isinstance(data["events"], list)


@pytest.mark.asyncio
async def test_list_presence_events_by_zone(client: AsyncClient):
    """Test filtering presence events by zone."""
    response = await client.get(
        "/api/presence/events",
        params={"zone_id": "cold-b"},
    )
    assert response.status_code == 200

    data = response.json()
    # All events should be for the specified zone
    for event in data["events"]:
        assert event["zoneId"] == "cold-b"


@pytest.mark.asyncio
async def test_presence_events_min_duration_filter(client: AsyncClient):
    """Test filtering presence events by minimum duration."""
    response = await client.get(
        "/api/presence/events",
        params={"min_duration": 300},  # 5 minutes
    )
    assert response.status_code == 200

    data = response.json()
    # All events should have at least 5 minutes duration
    for event in data["events"]:
        assert event["durationSeconds"] >= 300
