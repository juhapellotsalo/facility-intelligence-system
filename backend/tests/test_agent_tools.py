"""Tests for agent data query tools."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.tools import (
    get_baselines,
    get_door_events,
    get_thermal_presence,
    query_sensor_data,
)
from app.schemas.events import (
    DoorEvent,
    PresenceEvent,
    ReadingPoint,
    ReadingsResponse,
    SensorBaseline,
)


class TestDateParsing:
    """Tests for datetime parsing helper."""

    def test_parse_iso_with_z_suffix(self):
        """Test parsing ISO datetime with Z suffix."""
        from app.agent.tools import _parse_datetime

        result = _parse_datetime("2026-01-29T10:00:00Z")
        assert result == datetime(2026, 1, 29, 10, 0, 0)

    def test_parse_iso_with_timezone_offset(self):
        """Test parsing ISO datetime with timezone offset."""
        from app.agent.tools import _parse_datetime

        result = _parse_datetime("2026-01-29T10:00:00+00:00")
        assert result == datetime(2026, 1, 29, 10, 0, 0)

    def test_parse_iso_with_milliseconds(self):
        """Test parsing ISO datetime with milliseconds."""
        from app.agent.tools import _parse_datetime

        result = _parse_datetime("2026-01-29T10:00:00.123456")
        assert result == datetime(2026, 1, 29, 10, 0, 0, 123456)


class TestQuerySensorData:
    """Tests for query_sensor_data tool."""

    @pytest.mark.asyncio
    async def test_query_sensor_data_happy_path(self):
        """Test querying sensor data returns readings with summary."""
        mock_readings = ReadingsResponse(
            sensor_id="5",
            sensor_type="environmental",
            interval="raw",
            readings=[
                ReadingPoint(
                    timestamp=datetime(2026, 1, 29, 10, 0),
                    value=-17.5,
                    humidity=45.0,
                ),
                ReadingPoint(
                    timestamp=datetime(2026, 1, 29, 10, 15),
                    value=-17.2,
                    humidity=46.0,
                ),
            ],
        )

        with patch(
            "app.agent.tools.get_sensor_readings",
            new_callable=AsyncMock,
            return_value=mock_readings,
        ):
            result = await query_sensor_data.ainvoke(
                {
                    "sensor_id": "5",
                    "start": "2026-01-29T00:00:00",
                    "end": "2026-01-29T23:59:59",
                }
            )

        assert len(result["data"]) == 2
        assert "2 readings" in result["summary"]
        assert "-17.5°C" in result["summary"]
        assert "-17.2°C" in result["summary"]

    @pytest.mark.asyncio
    async def test_query_sensor_data_missing_params(self):
        """Test error when neither sensor_id nor zone_id provided."""
        result = await query_sensor_data.ainvoke(
            {
                "start": "2026-01-29T00:00:00",
                "end": "2026-01-29T23:59:59",
            }
        )

        assert result["data"] == []
        assert "Error" in result["summary"]

    @pytest.mark.asyncio
    async def test_query_sensor_data_not_found(self):
        """Test when sensor doesn't exist."""
        with patch(
            "app.agent.tools.get_sensor_readings",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await query_sensor_data.ainvoke(
                {
                    "sensor_id": "999",
                    "start": "2026-01-29T00:00:00",
                    "end": "2026-01-29T23:59:59",
                }
            )

        assert result["data"] == []
        assert "No sensor found" in result["summary"]

    @pytest.mark.asyncio
    async def test_query_sensor_data_by_zone(self):
        """Test querying sensor data by zone_id."""
        # Mock sensor config
        from unittest.mock import MagicMock

        mock_sensor = MagicMock()
        mock_sensor.id = "5"
        mock_sensor.label = "Cold Room B Temp"

        mock_readings = ReadingsResponse(
            sensor_id="5",
            sensor_type="environmental",
            interval="raw",
            readings=[
                ReadingPoint(timestamp=datetime(2026, 1, 29, 10, 0), value=-17.5, humidity=45.0),
            ],
        )

        with (
            patch(
                "app.agent.tools.get_sensors_by_zone",
                new_callable=AsyncMock,
                return_value=[mock_sensor],
            ),
            patch(
                "app.agent.tools.get_sensor_readings",
                new_callable=AsyncMock,
                return_value=mock_readings,
            ),
        ):
            result = await query_sensor_data.ainvoke(
                {
                    "zone_id": "3",
                    "start": "2026-01-29T00:00:00",
                    "end": "2026-01-29T23:59:59",
                }
            )

        assert len(result["data"]) == 1
        assert "zone 3" in result["summary"].lower()


class TestGetDoorEvents:
    """Tests for get_door_events tool."""

    @pytest.mark.asyncio
    async def test_get_door_events_happy_path(self):
        """Test getting door events returns events with summary."""
        mock_events = [
            DoorEvent(
                sensor_id="6",
                opened_at=datetime(2026, 1, 29, 8, 0),
                closed_at=datetime(2026, 1, 29, 8, 5),
                duration_seconds=300,
            ),
            DoorEvent(
                sensor_id="6",
                opened_at=datetime(2026, 1, 29, 10, 0),
                closed_at=datetime(2026, 1, 29, 10, 8),
                duration_seconds=480,
            ),
        ]

        with patch(
            "app.agent.tools.service_get_door_events",
            new_callable=AsyncMock,
            return_value=mock_events,
        ):
            result = await get_door_events.ainvoke(
                {
                    "sensor_id": "6",
                    "start": "2026-01-29T00:00:00",
                    "end": "2026-01-29T23:59:59",
                }
            )

        assert len(result["data"]) == 2
        assert "2 door events" in result["summary"]
        assert "8 minutes" in result["summary"]

    @pytest.mark.asyncio
    async def test_get_door_events_no_events(self):
        """Test when no door events found."""
        with patch(
            "app.agent.tools.service_get_door_events",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await get_door_events.ainvoke(
                {
                    "sensor_id": "6",
                    "start": "2026-01-29T00:00:00",
                    "end": "2026-01-29T23:59:59",
                }
            )

        assert result["data"] == []
        assert "No door events" in result["summary"]


class TestGetThermalPresence:
    """Tests for get_thermal_presence tool."""

    @pytest.mark.asyncio
    async def test_get_thermal_presence_with_safety_concern(self):
        """Test presence events flag safety concerns correctly."""
        mock_events = [
            PresenceEvent(
                sensor_id="7",
                zone_id="3",
                started_at=datetime(2026, 1, 29, 9, 0),
                ended_at=datetime(2026, 1, 29, 9, 5),
                duration_seconds=300,
                is_safety_concern=False,
            ),
            PresenceEvent(
                sensor_id="7",
                zone_id="3",
                started_at=datetime(2026, 1, 29, 10, 0),
                ended_at=datetime(2026, 1, 29, 10, 15),
                duration_seconds=900,
                is_safety_concern=True,
            ),
        ]

        with patch(
            "app.agent.tools.get_presence_events",
            new_callable=AsyncMock,
            return_value=mock_events,
        ):
            result = await get_thermal_presence.ainvoke(
                {
                    "sensor_id": "7",
                    "start": "2026-01-29T00:00:00",
                    "end": "2026-01-29T23:59:59",
                }
            )

        assert len(result["data"]) == 2
        assert "2 presence events" in result["summary"]
        assert "1 safety concern" in result["summary"]

    @pytest.mark.asyncio
    async def test_get_thermal_presence_no_events(self):
        """Test when no presence events found."""
        with patch(
            "app.agent.tools.get_presence_events",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await get_thermal_presence.ainvoke(
                {
                    "zone_id": "3",
                    "start": "2026-01-29T00:00:00",
                    "end": "2026-01-29T23:59:59",
                }
            )

        assert result["data"] == []
        assert "No presence events" in result["summary"]


class TestGetBaselines:
    """Tests for get_baselines tool."""

    @pytest.mark.asyncio
    async def test_get_baselines_happy_path(self):
        """Test getting baseline statistics."""
        mock_baseline = SensorBaseline(
            sensor_id="5",
            mean=-17.2,
            std_dev=0.5,
            min=-18.0,
            max=-16.5,
            unit="°C",
            sample_count=96,
            period_hours=24,
        )

        with patch(
            "app.agent.tools.get_sensor_baseline",
            new_callable=AsyncMock,
            return_value=mock_baseline,
        ):
            result = await get_baselines.ainvoke({"sensor_id": "5"})

        assert result["data"]["mean"] == -17.2
        assert result["data"]["std_dev"] == 0.5
        assert "-17.2°C ± 0.5°C" in result["summary"]

    @pytest.mark.asyncio
    async def test_get_baselines_not_found(self):
        """Test when sensor not found."""
        with patch(
            "app.agent.tools.get_sensor_baseline",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await get_baselines.ainvoke({"sensor_id": "999"})

        assert result["data"] == {}
        assert "No baseline data" in result["summary"]

    @pytest.mark.asyncio
    async def test_get_baselines_missing_sensor_id(self):
        """Test error when sensor_id not provided - Pydantic validation."""
        from pydantic import ValidationError

        # The tool uses Pydantic validation, so missing required field
        # raises ValidationError before the function runs
        with pytest.raises(ValidationError):
            await get_baselines.ainvoke({})
