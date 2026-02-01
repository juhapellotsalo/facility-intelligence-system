import type { SensorConfig } from "../data/sensors";

const API_BASE = "http://localhost:8000";

/**
 * Fetch all sensors
 */
export async function fetchSensors(): Promise<SensorConfig[]> {
  const response = await fetch("/api/sensors");
  if (!response.ok) {
    throw new Error(`Failed to fetch sensors: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Visualization idea from the agent
 */
export interface VisualizationIdea {
  id: string;
  title: string;
  description: string;
  icon: string;
  reasoning: string;
  spec: Record<string, unknown>;
}

/**
 * Visualization spec from the agent
 */
export interface VisualizationSpec {
  type: string;
  title: string;
  data: Record<string, unknown>;
  config: Record<string, unknown>;
  /** AI-generated JSX code for dynamic rendering */
  code?: string;
}

/**
 * SSE event types from the chat endpoint
 */
export interface ChatSSEEvent {
  type: "text" | "tool_use" | "done" | "error" | "visualization" | "ideas" | "progress";
  data: {
    content?: string;
    tool?: string;
    status?: string;
    message?: string;
    phase?: string;
    // Visualization response
    spec?: VisualizationSpec;
    ideaId?: string;
    title?: string;
    // Ideas response
    ideas?: VisualizationIdea[];
  };
}

/**
 * Chat with the agent via SSE streaming
 *
 * @param message - User message text
 * @param sessionId - Session ID for conversation continuity
 * @param onEvent - Callback for each SSE event
 * @returns Full response content
 */
export async function chatWithAgent(
  message: string,
  sessionId: string,
  onEvent: (event: ChatSSEEvent) => void = () => {},
): Promise<string> {
  const response = await fetch(`${API_BASE}/api/agent/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!response.ok) {
    throw new Error(`Agent request failed: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let fullContent = "";
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE events from buffer
    const lines = buffer.split("\n");
    buffer = lines.pop() || ""; // Keep incomplete line in buffer

    let eventType = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventType = line.slice(7);
      } else if (line.startsWith("data: ") && eventType) {
        try {
          const data = JSON.parse(line.slice(6));
          const event: ChatSSEEvent = {
            type: eventType as ChatSSEEvent["type"],
            data,
          };
          onEvent(event);

          if (eventType === "text" && data.content) {
            fullContent += data.content;
          } else if (eventType === "error") {
            throw new Error(data.message || "Agent error");
          }
        } catch (e) {
          if (e instanceof SyntaxError) {
            console.warn("Failed to parse SSE data:", line);
          } else {
            throw e;
          }
        }
        eventType = "";
      }
    }
  }

  return fullContent;
}
