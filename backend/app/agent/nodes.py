"""Agent graph nodes for the Facility Intelligence Assistant.

Contains all node implementations:
- router_node: Extract message type for routing
- chat_node: ReAct agent for conversation with tools
- ideation_node: Generate visualization ideas
- generate_node: Build visualization specs from data
"""

import json
import logging
from collections.abc import Sequence
from datetime import timedelta
from typing import Annotated, Any, Literal, TypedDict

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field

from app.agent.config import ZONES, get_codegen_llm, get_llm, get_viz_llm
from app.agent.prompts import (
    CODEGEN_PROMPT,
    DATA_GATHERING_PROMPT,
    IDEATION_PROMPT,
    get_system_prompt,
)
from app.agent.tools import get_all_tools
from app.database import get_session
from app.services import get_sensor_readings

logger = logging.getLogger(__name__)


# --- State Type (imported by graph.py) ---


class AgentState(TypedDict):
    """State schema for the Facility Intelligence Agent.

    Attributes:
        messages: Conversation history with automatic message accumulation.
        viz_messages: Visualization workflow messages (separate from chat history).
        message_type: Type of incoming message for routing (text, request_ideas, select_idea).
        selected_idea: The visualization idea selected by the user (for generate workflow).
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    viz_messages: Annotated[Sequence[BaseMessage], add_messages]
    message_type: str | None
    selected_idea: dict[str, Any] | None


# --- Router Node ---


def router_node(state: AgentState) -> dict:
    """Extract message type from the last human message and update state.

    Parses the content of the last HumanMessage to determine message type.
    Checks viz_messages first (for viz requests), then messages (for chat).
    Content can be:
    - Plain text string → type="text"
    - JSON with "type" field → extracted type
    """
    viz_messages = state.get("viz_messages", [])
    messages = state.get("messages", [])

    # Find the last human message - check viz_messages first
    last_message = None
    if viz_messages and isinstance(viz_messages[-1], HumanMessage):
        last_message = viz_messages[-1]
    elif messages and isinstance(messages[-1], HumanMessage):
        last_message = messages[-1]

    if not last_message:
        return {"message_type": "text", "selected_idea": None}

    content = last_message.content
    message_type = "text"
    selected_idea = None

    # Try to parse as JSON to extract type
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                message_type = parsed.get("type", "text")
                if message_type == "select_idea":
                    selected_idea = parsed.get("idea")
        except json.JSONDecodeError:
            message_type = "text"

    logger.debug(f"Router: {len(messages)} msgs, {len(viz_messages)} viz_msgs → {message_type}")
    return {"message_type": message_type, "selected_idea": selected_idea}


def route_by_message_type(
    state: AgentState,
) -> Literal["chat_node", "ideation_node", "generate_node"]:
    """Conditional edge function: route to appropriate node based on message type."""
    message_type = state.get("message_type", "text")

    if message_type == "request_ideas":
        return "ideation_node"
    elif message_type == "select_idea":
        return "generate_node"
    return "chat_node"


# --- Chat Node ---

_react_agent = None


async def _get_react_agent():
    """Get or create the inner ReAct agent for chat."""
    global _react_agent

    if _react_agent is None:
        from app.agent.graph import get_simulated_now

        simulated_now = await get_simulated_now()
        system_prompt = get_system_prompt(simulated_now)
        llm = get_llm()
        tools = get_all_tools()

        logger.info(f"Building ReAct agent with {len(tools)} tools")

        _react_agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt,
        )
        logger.info("ReAct agent ready")

    return _react_agent


# --- Data Gathering Agent ---

_data_agent = None


async def _get_data_agent():
    """Get or create the data gathering agent for visualizations.

    Uses Sonnet (via get_viz_llm) with all tools to intelligently gather
    data needed for visualization generation.
    """
    global _data_agent

    if _data_agent is None:
        from app.agent.graph import get_simulated_now

        simulated_now = await get_simulated_now()
        llm = get_viz_llm()  # Sonnet for reasoning
        tools = get_all_tools()

        system_prompt = DATA_GATHERING_PROMPT.format(
            current_time=simulated_now.strftime("%Y-%m-%d %H:%M"),
        )

        _data_agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt,
        )
        logger.info("Data gathering agent ready")

    return _data_agent


async def chat_node(state: AgentState) -> dict:
    """Process a text message using the ReAct agent.

    This node handles normal conversation with tool use.
    Returns the messages from the ReAct agent execution.
    """
    logger.debug(f"Chat node received {len(state.get('messages', []))} messages")

    agent = await _get_react_agent()

    # Run the ReAct agent
    result = await agent.ainvoke({"messages": state["messages"]})

    # Extract messages from result
    new_messages = result.get("messages", [])

    # Filter to only include new messages (those not in input)
    input_ids = {id(m) for m in state["messages"]}
    output_messages = [m for m in new_messages if id(m) not in input_ids]

    logger.debug(f"Chat node produced {len(output_messages)} messages")
    return {"messages": output_messages}


# --- Ideation Node ---


class VisualizationSpec(BaseModel):
    """Specification for generating a visualization."""

    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(description="Visualization type: zone-health, timeline, etc.")
    time_range: str = Field(
        default="24h",
        alias="timeRange",
        description="Time range: 1h, 24h, 7d",
    )
    zones: list[str] | None = Field(default=None, description="Zone IDs to include")
    sensors: list[str] | None = Field(default=None, description="Sensor IDs to include")
    metrics: list[str] | None = Field(default=None, description="Metrics to show")


class VisualizationIdea(BaseModel):
    """A single visualization idea."""

    id: str = Field(description="Unique identifier for the idea")
    title: str = Field(description="Short, descriptive title")
    description: str = Field(description="What the visualization will show")
    icon: str = Field(description="Icon name: thermometer, activity, clock, layers, zap")
    reasoning: str = Field(description="Why this is relevant to the conversation")
    spec: VisualizationSpec = Field(description="Parameters for generating the visualization")


class IdeasResponse(BaseModel):
    """Response containing visualization ideas."""

    ideas: list[VisualizationIdea] = Field(description="List of 3-4 visualization ideas")


async def ideation_node(state: AgentState) -> dict:
    """Generate visualization ideas based on conversation history.

    Analyzes the conversation to suggest relevant visualizations.
    Returns an AIMessage with type="ideas" containing the ideas list.
    """
    llm = get_viz_llm()
    structured_llm = llm.with_structured_output(IdeasResponse)

    # Build context from conversation history
    conversation_context = []
    for msg in state.get("messages", []):
        if isinstance(msg, HumanMessage):
            content = msg.content
            if isinstance(content, str) and not content.startswith("{"):
                conversation_context.append(f"User: {content}")
        elif isinstance(msg, AIMessage):
            content = msg.content
            if isinstance(content, str) and not content.startswith("{"):
                conversation_context.append(f"Assistant: {content[:200]}...")

    context_text = "\n".join(conversation_context[-10:])  # Last 10 messages

    messages = [
        SystemMessage(content=IDEATION_PROMPT),
        HumanMessage(
            content=f"""## Conversation History

{context_text or "No prior conversation - suggest general facility visualizations."}

Generate 3-4 relevant visualization ideas."""
        ),
    ]

    logger.debug(f"Ideation: {len(state.get('messages', []))} messages in context")

    try:
        response: IdeasResponse = await structured_llm.ainvoke(messages)
        ideas = [idea.model_dump(by_alias=True) for idea in response.ideas]
        logger.info(f"Generated {len(ideas)} visualization ideas")
    except Exception as e:
        logger.warning(f"Structured output failed: {e}, using defaults")
        ideas = _get_default_ideas()

    ideas_response = {"type": "ideas", "ideas": ideas}
    return {"viz_messages": [AIMessage(content=json.dumps(ideas_response))]}


def _get_default_ideas() -> list:
    """Return default visualization ideas when generation fails."""
    return [
        {
            "id": "zone-health-1",
            "title": "Zone Health Overview",
            "description": "Current temperatures across all zones compared to targets",
            "icon": "thermometer",
            "reasoning": "Get a quick overview of facility status",
            "spec": {"type": "zone-health", "timeRange": "24h"},
        },
        {
            "id": "timeline-all",
            "title": "24-Hour Temperature Timeline",
            "description": "Temperature readings across all zones for the past 24 hours",
            "icon": "clock",
            "reasoning": "See how temperatures have changed over time",
            "spec": {"type": "timeline", "timeRange": "24h", "metrics": ["temperature"]},
        },
        {
            "id": "heatmap-doors",
            "title": "Door Activity Heatmap",
            "description": "Door open/close patterns by hour and day",
            "icon": "activity",
            "reasoning": "Understand facility usage patterns",
            "spec": {"type": "heatmap", "metric": "door_opens", "timeRange": "7d"},
        },
    ]


# --- Generate Node ---


def _extract_gathered_data(agent_result: dict) -> tuple[dict | None, str | None]:
    """Extract tool results from data agent execution into visualization data.

    Parses the messages from the agent execution to find tool result messages,
    extracts their content, and builds a consolidated data structure.

    Returns:
        Tuple of (gathered_data, schema_description) or (None, None) if no useful data.
    """
    messages = agent_result.get("messages", [])

    gathered: dict[str, Any] = {
        "readings": [],
        "door_events": [],
        "presence_events": [],
        "baselines": {},
        "zones": [],
    }

    # Extract data from tool result messages
    for msg in messages:
        # Tool result messages have a 'name' attribute (the tool name)
        if hasattr(msg, "name") and msg.name:
            try:
                content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                tool_name = msg.name

                if tool_name == "query_sensor_data":
                    data = content.get("data", [])
                    if isinstance(data, list):
                        gathered["readings"].extend(data)
                elif tool_name == "get_door_events":
                    data = content.get("data", [])
                    if isinstance(data, list):
                        gathered["door_events"].extend(data)
                elif tool_name == "get_thermal_presence":
                    data = content.get("data", [])
                    if isinstance(data, list):
                        gathered["presence_events"].extend(data)
                elif tool_name == "get_baselines":
                    data = content.get("data", {})
                    if isinstance(data, dict):
                        sensor_id = data.get("sensor_id")
                        if sensor_id:
                            gathered["baselines"][sensor_id] = data
            except (json.JSONDecodeError, TypeError, AttributeError) as e:
                tool_name = getattr(msg, "name", "unknown")
                logger.debug(f"Could not parse tool result from {tool_name}: {e}")
                continue

    # Check if we got any useful data
    has_data = any(
        [
            gathered["readings"],
            gathered["door_events"],
            gathered["presence_events"],
            gathered["baselines"],
        ]
    )

    if not has_data:
        logger.warning("Data agent didn't gather any useful data")
        return None, None

    # Build schema description based on what data we have
    schema_parts = []
    if gathered["readings"]:
        schema_parts.append(
            "data.readings: Array of sensor readings with "
            "{timestamp, value, humidity, sensor_id?, sensor_name?}"
        )
    if gathered["door_events"]:
        schema_parts.append(
            "data.door_events: Array of door events with "
            "{sensor_id, opened_at, closed_at, duration_seconds}"
        )
    if gathered["presence_events"]:
        schema_parts.append(
            "data.presence_events: Array of presence events with "
            "{sensor_id, zone_id, started_at, ended_at, duration_seconds, is_safety_concern}"
        )
    if gathered["baselines"]:
        schema_parts.append(
            "data.baselines: Object keyed by sensor_id, values have "
            "{sensor_id, mean, std_dev, min, max, unit}"
        )

    schema = "\n".join(schema_parts)

    logger.info(
        f"Data agent gathered: {len(gathered['readings'])} readings, "
        f"{len(gathered['door_events'])} door events, "
        f"{len(gathered['presence_events'])} presence events, "
        f"{len(gathered['baselines'])} baselines"
    )

    return gathered, schema


async def generate_node(state: AgentState) -> dict:
    """Generate a visualization using a two-step approach.

    Step 1: Data Gathering Agent (Sonnet) - Reasons about what data is needed
            and calls appropriate tools intelligently based on the visualization type.
    Step 2: Code Generation (Opus) - Generates beautiful JSX with enhanced design guidance.

    Emits progress events via get_stream_writer() for real-time feedback.
    Falls back to legacy data fetching if the agent doesn't return useful data.
    """
    # Get stream writer for emitting progress events
    writer = get_stream_writer()

    selected_idea = state.get("selected_idea")
    if not selected_idea:
        logger.warning("No selected idea in state")
        error_response = {
            "type": "error",
            "message": "No visualization idea selected",
        }
        return {"viz_messages": [AIMessage(content=json.dumps(error_response))]}

    idea_type = selected_idea.get("spec", {}).get("type", "zone-health")
    idea_title = selected_idea.get("title", "Visualization")
    idea_spec = selected_idea.get("spec", {})
    idea_description = selected_idea.get("description", "")
    time_range = idea_spec.get("timeRange", "24h")

    logger.info(f"Generating visualization: {idea_title} (type={idea_type})")

    # Emit: Starting data gathering
    writer({"event": "progress", "phase": "gathering", "message": "Gathering facility data..."})

    # Step 1: Use data agent to gather appropriate data
    data_agent = await _get_data_agent()

    gather_request = f"""Gather data for this visualization:
- Title: {idea_title}
- Type: {idea_type}
- Description: {idea_description}
- Time Range: {time_range}

Fetch the appropriate data using the available tools. Think about what this visualization needs:
- For zone-health: get current readings from all zone sensors
- For timeline/trend: get time series data with baselines
- For heatmap/activity: get door events AND thermal presence events
- For comparison: get data from multiple zones with baselines"""

    try:
        # Stream the data agent to capture tool calls in real-time
        agent_result = None
        async for event in data_agent.astream_events(
            {"messages": [HumanMessage(content=gather_request)]},
            version="v2",
        ):
            event_type = event.get("event")
            event_name = event.get("name", "")

            # Emit tool start events
            if event_type == "on_tool_start":
                tool_name = event_name
                # Make tool names more user-friendly
                friendly_names = {
                    "query_sensor_data": "Querying sensor data",
                    "get_door_events": "Fetching door events",
                    "get_thermal_presence": "Checking presence data",
                    "get_baselines": "Loading baselines",
                }
                friendly = friendly_names.get(tool_name, f"Using {tool_name}")
                writer({
                    "event": "tool",
                    "phase": "gathering",
                    "tool": tool_name,
                    "status": "running",
                    "message": f"{friendly}...",
                })

            # Emit tool end events
            elif event_type == "on_tool_end":
                tool_name = event_name
                writer({
                    "event": "tool",
                    "phase": "gathering",
                    "tool": tool_name,
                    "status": "done",
                    "message": "Done",
                })

            # Capture final output
            elif event_type == "on_chain_end" and event_name == "LangGraph":
                agent_result = event.get("data", {}).get("output", {})

        # Step 2: Extract tool results from agent execution
        gathered_data, data_schema = _extract_gathered_data(agent_result or {})

        # Emit: Data gathered summary
        if gathered_data:
            summary_parts = []
            if gathered_data.get("readings"):
                summary_parts.append(f"{len(gathered_data['readings'])} readings")
            if gathered_data.get("door_events"):
                summary_parts.append(f"{len(gathered_data['door_events'])} door events")
            if gathered_data.get("presence_events"):
                summary_parts.append(f"{len(gathered_data['presence_events'])} presence events")
            if summary_parts:
                writer({
                    "event": "progress",
                    "phase": "gathering",
                    "message": f"Collected {', '.join(summary_parts)}",
                })

    except Exception as e:
        logger.warning(f"Data agent failed: {e}, using fallback")
        writer({"event": "progress", "phase": "gathering", "message": "Using fallback data..."})
        gathered_data, data_schema = None, None

    # Fallback to legacy fetching if agent didn't return useful data
    if gathered_data is None:
        logger.info("Using fallback data fetching")
        gathered_data, data_schema = await _fetch_visualization_data(idea_type, idea_spec)

    # Emit: Starting code generation
    writer({"event": "progress", "phase": "generating", "message": "Generating visualization..."})

    # Step 3: Generate code with Opus
    code = await _generate_visualization_code(
        viz_type=idea_type,
        title=idea_title,
        description=idea_description,
        data=gathered_data,
        data_schema=data_schema,
    )

    # Emit: Complete
    writer({"event": "progress", "phase": "complete", "message": "Visualization ready"})

    # Step 4: Return visualization response
    viz_response = {
        "type": "visualization",
        "ideaId": selected_idea.get("id", "generated"),
        "title": idea_title,
        "spec": {
            "type": idea_type,
            "title": idea_title,
            "data": gathered_data,
            "config": idea_spec,
            "code": code,  # AI-generated JSX
        },
    }

    logger.info(f"Generated visualization with Opus for {idea_title}")
    return {"viz_messages": [AIMessage(content=json.dumps(viz_response))]}


async def _fetch_visualization_data(viz_type: str, spec: dict) -> tuple[dict, str]:
    """Fetch visualization data and return (data_dict, schema_description)."""
    from app.agent.graph import get_simulated_now

    simulated_now = await get_simulated_now()

    time_range = spec.get("timeRange", "24h")
    hours = _parse_time_range(time_range)
    start_time = simulated_now - timedelta(hours=hours)

    try:
        async with get_session() as session:
            if viz_type == "zone-health":
                zones_data = await _fetch_zone_health_data(session, simulated_now)
                data = {"zones": zones_data}
                schema = """
data.zones: Array of zone objects with:
  - id: string (zone ID like "Z1", "Z2")
  - name: string (display name like "Loading Bay", "Cold Room A")
  - currentTemp: number (current temperature in Celsius)
  - targetMin: number (minimum target temperature)
  - targetMax: number (maximum target temperature)
  - status: string ("normal", "cold", or "warm")
"""
                return data, schema

            elif viz_type in ("timeline", "trend"):
                sensor_id = spec.get("sensor", "cold-a-temp")
                series_data = await _fetch_series_data(
                    session, sensor_id, start_time, simulated_now
                )
                data = {"series": series_data, "sensor": sensor_id}
                schema = """
data.series: Array of time-series data points with:
  - time: string (ISO timestamp)
  - value: number (temperature reading in Celsius)
data.sensor: string (sensor ID)
"""
                return data, schema

            elif viz_type == "comparison":
                zones = spec.get("zones", ["Z2", "Z3"])
                comparison_data = await _fetch_comparison_data(session, zones, simulated_now)
                data = {"zones": comparison_data}
                schema = """
data.zones: Array of zone objects for comparison with:
  - id: string (zone ID)
  - name: string (display name)
  - values: object containing:
    - temp: number (current temperature in Celsius)
"""
                return data, schema

            elif viz_type == "heatmap":
                # For heatmap, we'll fetch door events or other activity data
                zones_data = await _fetch_zone_health_data(session, simulated_now)
                data = {"zones": zones_data}
                schema = """
data.zones: Array of zone objects with activity data:
  - id: string (zone ID)
  - name: string (display name)
  - currentTemp: number (current temperature)
  - targetMin: number, targetMax: number (target range)
  - status: string ("normal", "cold", or "warm")
"""
                return data, schema

            else:
                # Default to zone-health
                zones_data = await _fetch_zone_health_data(session, simulated_now)
                data = {"zones": zones_data}
                schema = """
data.zones: Array of zone objects with:
  - id: string (zone ID)
  - name: string (display name)
  - currentTemp: number (current temperature in Celsius)
  - targetMin: number, targetMax: number (target range)
  - status: string ("normal", "cold", or "warm")
"""
                return data, schema

    except Exception as e:
        logger.error(f"Error fetching data for visualization: {e}")
        return {"error": str(e)}, "data.error: string (error message)"


async def _generate_visualization_code(
    viz_type: str, title: str, description: str, data: dict, data_schema: str
) -> str:
    """Generate JSX code using Opus."""
    llm = get_codegen_llm()

    # Truncate sample data to avoid token limits
    sample_data = json.dumps(data, indent=2, default=str)[:2000]

    prompt = CODEGEN_PROMPT.format(
        data_schema=data_schema.strip(),
        sample_data=sample_data,
        viz_type=viz_type,
        title=title,
        description=description,
    )

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        code = response.content.strip()

        # Strip markdown code blocks if present
        if code.startswith("```"):
            # Remove opening fence (```jsx or ```)
            first_newline = code.find("\n")
            code = code[first_newline + 1 :] if first_newline != -1 else code[3:]
        if code.endswith("```"):
            code = code[:-3]

        return code.strip()
    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        return '<div className="p-4 text-red-400">Code generation failed</div>'


async def _fetch_zone_health_data(session, simulated_now) -> list:
    """Fetch current temperature data for all zones."""
    zones_data = []
    for zone_id, zone_config in ZONES.items():
        sensor_id = zone_config["sensor_id"]
        target_min = zone_config["temp_min"]
        target_max = zone_config["temp_max"]
        zone_name = zone_config["name"]

        result = await get_sensor_readings(
            session,
            sensor_id,
            simulated_now - timedelta(hours=1),
            simulated_now,
            "raw",
        )
        current_temp = None
        if result and result.readings:
            current_temp = result.readings[-1].value

        status = "normal"
        if current_temp is not None:
            if current_temp < target_min:
                status = "cold"
            elif current_temp > target_max:
                status = "warm"

        zones_data.append(
            {
                "id": zone_id,
                "name": zone_name,
                "currentTemp": current_temp,
                "targetMin": target_min,
                "targetMax": target_max,
                "status": status,
            }
        )

    return zones_data


async def _fetch_series_data(session, sensor_id, start_time, end_time) -> list:
    """Fetch time series data for a sensor."""
    result = await get_sensor_readings(session, sensor_id, start_time, end_time, "raw")
    if result and result.readings:
        return [{"time": r.timestamp.isoformat(), "value": r.value} for r in result.readings]
    return []


async def _fetch_comparison_data(session, zones, simulated_now) -> list:
    """Fetch comparison data for specified zones."""
    comparison_data = []
    for zone_id in zones:
        zone_config = ZONES.get(zone_id, {})
        sensor_id = zone_config.get("sensor_id", "cold-a-temp")
        zone_name = zone_config.get("name", zone_id)

        result = await get_sensor_readings(
            session,
            sensor_id,
            simulated_now - timedelta(hours=1),
            simulated_now,
            "raw",
        )
        temp = None
        if result and result.readings:
            temp = result.readings[-1].value

        comparison_data.append(
            {
                "id": zone_id,
                "name": zone_name,
                "values": {"temp": temp},
            }
        )

    return comparison_data


def _parse_time_range(time_range: str) -> int:
    """Parse time range string to hours."""
    if time_range.endswith("h"):
        return int(time_range[:-1])
    elif time_range.endswith("d"):
        return int(time_range[:-1]) * 24
    return 24  # Default to 24 hours
