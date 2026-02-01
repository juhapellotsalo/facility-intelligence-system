import type { ChartSpec } from "../components/panel/ChatChart";
import type { ReportSpec } from "../components/panel/ChatReport";

/**
 * Chat message type used by the assistant panel.
 */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  chart?: ChartSpec;
  report?: ReportSpec;
  toolStatus?: string;
  isReport?: boolean;
  timestamp: Date;
}

/**
 * Get the initial welcome message.
 */
export function getWelcomeMessage(): Omit<ChatMessage, "id"> {
  return {
    role: "assistant",
    content: `**Facility Assistant**

I monitor your facility and can answer questions about temperatures, door activity, air quality, and worker safety.

Type a question or click [[Help|help]] to see what I can do.`,
    timestamp: new Date(),
  };
}

/**
 * Get the static help response with suggested actions.
 */
export function getHelpMessage(): Omit<ChatMessage, "id"> {
  return {
    role: "assistant",
    content: `**📋 What I Can Help With**

**Status & Analysis**
• [[Quick facility status|What's the current status across all zones?]] — Overview of all zones and active alerts
• [[Energy efficiency review|Where am I wasting energy?]] — Find cost-saving opportunities
• [[Air quality check|How is Loading Bay Air Quality doing?]] — CO₂ levels and ventilation
• [[Door activity summary|Show me door events]] — Recent access patterns across zones

**Reports**
• [[Generate incident report|Generate incident report]] — Document temperature excursions
• [[Audit prep|Prepare audit package]] — Health & safety inspection readiness`,
    timestamp: new Date(),
  };
}

/**
 * Generate a unique message ID.
 */
export function generateMessageId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}
