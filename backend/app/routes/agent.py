"""Agent endpoints with clean separation of concerns.

Endpoints:
- POST /api/agent/chat - Text chat with SSE streaming
- POST /api/agent/ideas - Generate visualization ideas (JSON)
- POST /api/agent/visualize - Generate visualization from idea (JSON)
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from app.agent import get_agent
from app.agent.graph import get_thread_config
from app.config import AGENT_TIMEOUT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


# --- Request/Response Models ---


class ChatRequest(BaseModel):
    """Request for text chat endpoint."""

    message: str = Field(..., description="User message text")
    session_id: str = Field(..., description="Session ID for conversation continuity")


class IdeasRequest(BaseModel):
    """Request for visualization ideas endpoint."""

    session_id: str = Field(..., description="Session ID for conversation context")


class VisualizeRequest(BaseModel):
    """Request for visualization generation endpoint."""

    session_id: str = Field(..., description="Session ID for conversation context")
    idea: dict[str, Any] = Field(..., description="Selected visualization idea")


class IdeasResponse(BaseModel):
    """Response containing visualization ideas."""

    ideas: list[dict[str, Any]]


class VisualizeResponse(BaseModel):
    """Response containing generated visualization."""

    idea_id: str
    title: str
    spec: dict[str, Any]


# --- SSE Helpers ---


def sse_event(event_type: str, data: dict) -> str:
    """Format data as an SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


# --- Endpoints ---


@router.post("/chat")
async def chat(request: ChatRequest):
    """Stream text chat response via Server-Sent Events.

    SSE Event Types:
    - text: Text content from the agent (intermediate or final)
    - tool_use: Tool being called (status: running/done)
    - visualization: Generated visualization spec
    - ideas: Generated visualization ideas
    - done: Stream complete
    - error: Error occurred

    Special message types (JSON with "type" field):
    - generate_viz: Generate visualization from an idea
    - request_ideas: Request visualization ideas based on conversation
    """
    logger.info(f"Chat: session={request.session_id}, message={request.message[:50]}...")

    # Parse message to check for special types
    msg_type = "text"
    msg_data: dict[str, Any] = {}
    try:
        msg_data = json.loads(request.message)
        msg_type = msg_data.get("type", "text")
    except json.JSONDecodeError:
        msg_type = "text"

    async def event_stream():
        try:
            agent = await get_agent()
            config = get_thread_config(request.session_id)

            # Route based on message type
            if msg_type == "generate_viz":
                # Handle visualization generation with custom streaming
                idea = msg_data.get("idea", {})
                title = idea.get("title", "visualization")
                yield sse_event("text", {"content": f'Generating "{title}"...'})

                # Send select_idea message to viz_messages channel
                message_content = json.dumps({"type": "select_idea", "idea": idea})
                visualization_data: dict[str, Any] | None = None

                async with asyncio.timeout(AGENT_TIMEOUT):
                    # Use combined stream modes: custom for progress, updates for final state
                    async for stream_mode, chunk in agent.astream(
                        {"viz_messages": [HumanMessage(content=message_content)]},
                        config,
                        stream_mode=["custom", "updates"],
                    ):
                        if stream_mode == "custom":
                            # Custom events from generate_node
                            event_data = chunk
                            if isinstance(event_data, dict):
                                event_type = event_data.get("event")
                                if event_type == "progress":
                                    yield sse_event("progress", {
                                        "phase": event_data.get("phase", ""),
                                        "message": event_data.get("message", ""),
                                    })
                                elif event_type == "tool":
                                    yield sse_event("tool_use", {
                                        "tool": event_data.get("tool", ""),
                                        "status": event_data.get("status", ""),
                                        "message": event_data.get("message", ""),
                                    })

                        elif stream_mode == "updates":
                            # State updates - format is {node_name: state_delta}
                            if isinstance(chunk, dict):
                                # Check each node's output for viz_messages
                                for node_output in chunk.values():
                                    if not isinstance(node_output, dict):
                                        continue
                                    viz_msgs = node_output.get("viz_messages", [])
                                    for msg in viz_msgs:
                                        if hasattr(msg, "content"):
                                            try:
                                                data = json.loads(msg.content)
                                                if data.get("type") in ("visualization", "error"):
                                                    visualization_data = data
                                            except (json.JSONDecodeError, TypeError):
                                                pass

                # Emit the visualization result
                if visualization_data:
                    if visualization_data.get("type") == "visualization":
                        yield sse_event(
                            "visualization",
                            {
                                "ideaId": visualization_data.get("ideaId", ""),
                                "title": visualization_data.get("title", ""),
                                "spec": visualization_data.get("spec", {}),
                            },
                        )
                    elif visualization_data.get("type") == "error":
                        err_msg = visualization_data.get("message", "Generation failed")
                        yield sse_event("error", {"message": err_msg})
                else:
                    yield sse_event("error", {"message": "No visualization generated"})

            elif msg_type == "request_ideas":
                # Handle ideas request with streaming
                yield sse_event("text", {"content": "Analyzing conversation..."})

                async with asyncio.timeout(AGENT_TIMEOUT):
                    result = await agent.ainvoke(
                        {"viz_messages": [HumanMessage(content='{"type": "request_ideas"}')]},
                        config,
                    )

                # Extract ideas from response
                for msg in result.get("viz_messages", []):
                    if isinstance(msg, AIMessage) and msg.content:
                        try:
                            data = json.loads(msg.content)
                            if data.get("type") == "ideas":
                                yield sse_event("ideas", {"ideas": data.get("ideas", [])})
                        except json.JSONDecodeError:
                            pass

            else:
                # Normal chat flow with progress events
                final_text = ""
                active_tools: set[str] = set()
                has_emitted_thinking = False

                # Friendly tool names for UI display
                friendly_tool_names = {
                    "query_sensor_data": "Querying sensor readings",
                    "get_door_events": "Checking door activity",
                    "get_thermal_presence": "Checking motion sensors",
                    "get_baselines": "Loading baseline data",
                }

                async with asyncio.timeout(AGENT_TIMEOUT):
                    async for event in agent.astream_events(
                        {"messages": [HumanMessage(content=request.message)]},
                        config,
                        version="v2",
                    ):
                        event_type = event.get("event")
                        event_name = event.get("name", "")

                        # Emit "thinking" on first LLM start
                        if event_type == "on_chat_model_start" and not has_emitted_thinking:
                            yield sse_event("progress", {"message": "Analyzing your question..."})
                            has_emitted_thinking = True

                        # Tool starting
                        elif event_type == "on_tool_start":
                            tool_name = event_name
                            if tool_name and tool_name not in active_tools:
                                active_tools.add(tool_name)
                                friendly = friendly_tool_names.get(tool_name, f"Using {tool_name}")
                                yield sse_event(
                                    "tool_use",
                                    {"tool": tool_name, "status": "running", "message": f"{friendly}..."},
                                )

                        # Tool finished
                        elif event_type == "on_tool_end":
                            tool_name = event_name
                            if tool_name and tool_name in active_tools:
                                active_tools.discard(tool_name)
                                yield sse_event(
                                    "tool_use",
                                    {"tool": tool_name, "status": "done", "message": "Done"},
                                )

                        # Chat model finished - check if this is intermediate or final
                        elif event_type == "on_chat_model_end":
                            output = event.get("data", {}).get("output")
                            if output:
                                # Extract text content
                                content = ""
                                if hasattr(output, "content"):
                                    content = output.content
                                    if isinstance(content, list):
                                        content = "".join(
                                            block.get("text", "")
                                            for block in content
                                            if isinstance(block, dict)
                                            and block.get("type") == "text"
                                        )

                                # Check if this LLM call has tool calls (intermediate)
                                has_tool_calls = hasattr(output, "tool_calls") and output.tool_calls

                                if has_tool_calls and content:
                                    # Intermediate thinking text before tool calls
                                    yield sse_event("text", {"content": content})
                                elif content:
                                    # No tool calls = this is the final answer
                                    # Store it; we'll emit on done
                                    final_text = content

                # Emit final answer
                if final_text:
                    yield sse_event("text", {"content": final_text})

        except TimeoutError:
            logger.warning(f"Chat timeout after {AGENT_TIMEOUT}s")
            yield sse_event("error", {"message": f"Timeout after {AGENT_TIMEOUT}s"})

        except Exception as e:
            logger.exception("Chat error")
            yield sse_event("error", {"message": str(e)})

        yield sse_event("done", {})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/ideas", response_model=IdeasResponse)
async def get_ideas(request: IdeasRequest):
    """Generate visualization ideas based on conversation history.

    Returns a list of visualization ideas with specs.
    """
    logger.info(f"Ideas: session={request.session_id}")

    try:
        async with asyncio.timeout(AGENT_TIMEOUT):
            agent = await get_agent()
            config = get_thread_config(request.session_id)

            # Send request_ideas message to viz_messages channel
            result = await agent.ainvoke(
                {"viz_messages": [HumanMessage(content='{"type": "request_ideas"}')]},
                config,
            )

            # Extract ideas from response
            for msg in result.get("viz_messages", []):
                if isinstance(msg, AIMessage) and msg.content:
                    try:
                        data = json.loads(msg.content)
                        if data.get("type") == "ideas":
                            return IdeasResponse(ideas=data.get("ideas", []))
                    except json.JSONDecodeError:
                        pass

            return IdeasResponse(ideas=[])

    except TimeoutError:
        raise HTTPException(504, f"Timeout after {AGENT_TIMEOUT}s") from None
    except Exception as e:
        logger.exception("Ideas error")
        raise HTTPException(500, str(e)) from e


@router.post("/visualize", response_model=VisualizeResponse)
async def visualize(request: VisualizeRequest):
    """Generate a visualization from a selected idea.

    Returns the visualization spec with data.
    """
    logger.info(f"Visualize: session={request.session_id}, idea={request.idea.get('id')}")

    try:
        async with asyncio.timeout(AGENT_TIMEOUT):
            agent = await get_agent()
            config = get_thread_config(request.session_id)

            # Send select_idea message to viz_messages channel
            message_content = json.dumps(
                {
                    "type": "select_idea",
                    "idea": request.idea,
                }
            )
            result = await agent.ainvoke(
                {"viz_messages": [HumanMessage(content=message_content)]},
                config,
            )

            # Extract visualization from response
            for msg in result.get("viz_messages", []):
                if isinstance(msg, AIMessage) and msg.content:
                    try:
                        data = json.loads(msg.content)
                        if data.get("type") == "visualization":
                            return VisualizeResponse(
                                idea_id=data.get("ideaId", ""),
                                title=data.get("title", ""),
                                spec=data.get("spec", {}),
                            )
                        elif data.get("type") == "error":
                            raise HTTPException(400, data.get("message", "Generation failed"))
                    except json.JSONDecodeError:
                        pass

            raise HTTPException(500, "No visualization generated")

    except TimeoutError:
        raise HTTPException(504, f"Timeout after {AGENT_TIMEOUT}s") from None
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Visualize error")
        raise HTTPException(500, str(e)) from e
