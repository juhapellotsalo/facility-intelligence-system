"""Configuration for the Facility Intelligence Agent.

Centralizes LLM settings and facility zone/sensor definitions.
"""

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

# --- LLM Configuration ---

PROVIDER = "anthropic"  # "anthropic" or "openai"

MODEL_HAIKU = "claude-haiku-4-5"
MODEL_SONNET = "claude-sonnet-4-5"
MODEL_OPUS = "claude-opus-4-5"

CHAT_MODEL = MODEL_SONNET  # Smarter model for interactive chat
VIZ_MODEL = MODEL_SONNET  # Smarter model for visualization ideation
CODEGEN_MODEL = MODEL_OPUS  # Opus for visualization code generation


def get_llm():
    """Get the configured LLM instance for chat/tools."""
    if PROVIDER == "anthropic":
        return ChatAnthropic(model=CHAT_MODEL)
    return ChatOpenAI(model=CHAT_MODEL)


def get_viz_llm():
    """Get the LLM instance for visualization tasks (ideation, generation)."""
    if PROVIDER == "anthropic":
        return ChatAnthropic(model=VIZ_MODEL)
    return ChatOpenAI(model=VIZ_MODEL)


def get_codegen_llm():
    """Get the LLM instance for visualization code generation (uses Opus)."""
    if PROVIDER == "anthropic":
        return ChatAnthropic(model=CODEGEN_MODEL, max_tokens=4096)
    return ChatOpenAI(model=CODEGEN_MODEL, max_tokens=4096)


# --- Facility Zone Configuration ---
# Central source of truth for zone/sensor definitions

ZONES = {
    "Z1": {
        "name": "Loading Bay",
        "description": "Ambient storage",
        "temp_min": 15,
        "temp_max": 25,
        "sensor_id": "loading-temp",
    },
    "Z2": {
        "name": "Cold Room A",
        "description": "Fresh storage",
        "temp_min": 2,
        "temp_max": 4,
        "sensor_id": "cold-a-temp",
    },
    "Z3": {
        "name": "Cold Room B",
        "description": "Freezer",
        "temp_min": -20,
        "temp_max": -16,
        "sensor_id": "cold-b-temp",
    },
    "Z4": {
        "name": "Dry Storage",
        "description": "Ambient storage",
        "temp_min": 15,
        "temp_max": 20,
        "sensor_id": "dry-temp",
    },
}


def get_zone_sensor(zone_id: str) -> str:
    """Get the primary temperature sensor ID for a zone."""
    return ZONES.get(zone_id, {}).get("sensor_id", "cold-a-temp")


def get_zone_name(zone_id: str) -> str:
    """Get the display name for a zone."""
    return ZONES.get(zone_id, {}).get("name", zone_id)


def get_zone_targets(zone_id: str) -> tuple[int, int]:
    """Get the target temperature range for a zone."""
    zone = ZONES.get(zone_id, {})
    return zone.get("temp_min", 0), zone.get("temp_max", 25)
