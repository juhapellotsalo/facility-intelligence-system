"""LangGraph agent definition for the Facility Intelligence Assistant.

Uses a custom StateGraph with message-type routing to support:
- Normal chat (ReAct pattern with tools)
- Visualization ideation (generate ideas from conversation)
- Visualization generation (create visualization from selected idea)

Also contains:
- Simulated time context (get_simulated_now)
- Checkpointer singleton
"""

import logging
from datetime import datetime

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from sqlalchemy import func, select

from app.database import async_session
from app.models import EnvironmentalReading

logger = logging.getLogger(__name__)

# --- Simulated Time Context ---

_simulated_now: datetime | None = None


async def get_simulated_now() -> datetime:
    """Get the 'current time' for the demo based on database data.

    Returns the MAX(timestamp) from environmental readings, which represents
    when the facility manager 'arrives at work' in the demo scenario.

    Cached after first call since data doesn't change during a session.
    """
    global _simulated_now

    if _simulated_now is not None:
        return _simulated_now

    async with async_session() as session:
        result = await session.execute(select(func.max(EnvironmentalReading.timestamp)))
        max_ts = result.scalar_one_or_none()

        if max_ts is None:
            logger.warning("No sensor data found, using actual current time")
            _simulated_now = datetime.now()
        else:
            _simulated_now = max_ts
            logger.info(f"Simulated 'now' set to: {_simulated_now}")

    return _simulated_now


def clear_simulated_now_cache():
    """Clear the cached simulated time (useful after data regeneration)."""
    global _simulated_now
    _simulated_now = None


# --- Checkpointer ---

_checkpointer = None


def get_checkpointer() -> MemorySaver:
    """Get the singleton checkpointer instance."""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MemorySaver()
        logger.info("Created MemorySaver checkpointer")
    return _checkpointer


# --- Graph Building ---

_agent = None


def build_graph() -> StateGraph:
    """Build the Facility Intelligence Agent graph.

    Graph structure:
        Entry → router → conditional edge based on message_type
                         ├── chat_node (for text messages)
                         ├── ideation_node (for request_ideas)
                         └── generate_node (for select_idea)

    Returns:
        StateGraph: The uncompiled graph
    """
    from app.agent.nodes import (
        AgentState,
        chat_node,
        generate_node,
        ideation_node,
        route_by_message_type,
        router_node,
    )

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", router_node)
    graph.add_node("chat_node", chat_node)
    graph.add_node("ideation_node", ideation_node)
    graph.add_node("generate_node", generate_node)

    # Set entry point
    graph.set_entry_point("router")

    # Add conditional edges from router
    graph.add_conditional_edges(
        "router",
        route_by_message_type,
        {
            "chat_node": "chat_node",
            "ideation_node": "ideation_node",
            "generate_node": "generate_node",
        },
    )

    # All nodes end after execution
    graph.add_edge("chat_node", END)
    graph.add_edge("ideation_node", END)
    graph.add_edge("generate_node", END)

    return graph


async def build_agent():
    """Build and compile the Facility Intelligence Agent."""
    simulated_now = await get_simulated_now()
    logger.info(f"Building agent graph (simulated time: {simulated_now})")

    graph = build_graph()
    checkpointer = get_checkpointer()
    compiled = graph.compile(checkpointer=checkpointer)

    logger.info("Facility Intelligence Agent ready")
    return compiled


async def get_agent():
    """Get the singleton agent instance, creating it if needed."""
    global _agent
    if _agent is None:
        _agent = await build_agent()
    return _agent


def get_thread_config(thread_id: str) -> dict:
    """Get the config dict for a thread/session."""
    return {"configurable": {"thread_id": thread_id}}


async def stream_agent(state: dict, thread_id: str):
    """Stream agent execution for SSE support.

    Uses the main graph's astream method which includes checkpointing.
    This ensures conversation history is persisted and loaded correctly.

    Args:
        state: Input state (only new message needed, checkpointer has history)
        thread_id: Session/thread ID for checkpointer

    Yields:
        dict: Chunks from agent execution
    """
    agent = await get_agent()
    config = get_thread_config(thread_id)

    async for chunk in agent.astream(state, config):
        yield chunk
