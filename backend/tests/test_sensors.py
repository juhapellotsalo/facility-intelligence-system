"""Tests for sensor API endpoints."""

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


@pytest.mark.asyncio
async def test_list_sensors_returns_list(client: AsyncClient):
    """Test listing all sensors returns a list."""
    response = await client.get("/api/sensors")
    assert response.status_code == 200

    sensors = response.json()
    assert isinstance(sensors, list)
    assert len(sensors) > 0


@pytest.mark.asyncio
async def test_list_sensors_structure(client: AsyncClient):
    """Test sensor response structure."""
    response = await client.get("/api/sensors")
    assert response.status_code == 200

    sensors = response.json()
    sensor = sensors[0]

    # Check required fields exist
    assert "id" in sensor
    assert "sensorType" in sensor
    assert "zone" in sensor
    assert "label" in sensor
    assert "reading" in sensor
    assert "trend" in sensor
    assert "stats" in sensor

    # Check reading structure
    reading = sensor["reading"]
    assert "value" in reading
    assert "status" in reading
    assert reading["status"] in ["normal", "warning", "critical"]

    # Check trend is a list
    assert isinstance(sensor["trend"], list)

    # Check stats structure
    stats = sensor["stats"]
    assert "min" in stats
    assert "max" in stats
    assert "avg" in stats
    assert "unit" in stats


@pytest.mark.asyncio
async def test_get_sensor_by_id(client: AsyncClient):
    """Test getting a single sensor by ID."""
    # First get the list to find a valid ID
    list_response = await client.get("/api/sensors")
    sensors = list_response.json()
    sensor_id = sensors[0]["id"]

    # Now fetch that specific sensor
    response = await client.get(f"/api/sensors/{sensor_id}")
    assert response.status_code == 200

    sensor = response.json()
    assert sensor["id"] == sensor_id


@pytest.mark.asyncio
async def test_get_sensor_not_found(client: AsyncClient):
    """Test 404 for unknown sensor."""
    response = await client.get("/api/sensors/unknown-sensor-xyz")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_environmental_sensor_has_thresholds(client: AsyncClient):
    """Test that environmental sensors have thresholds."""
    response = await client.get("/api/sensors")
    sensors = response.json()

    # Find an environmental sensor
    env_sensor = next(
        (s for s in sensors if s["sensorType"] == "environmental"),
        None,
    )

    if env_sensor:
        assert env_sensor["thresholds"] is not None
        assert "warning" in env_sensor["thresholds"]
        assert "critical" in env_sensor["thresholds"]
