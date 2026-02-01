import type { VisualizationIdea } from "./VisualizationIdeas";

/**
 * Default visualization ideas shown when no AI-generated ideas exist.
 * These let users quickly explore common visualizations without chat context.
 */
export const DEFAULT_IDEAS: VisualizationIdea[] = [
  {
    id: "zone-health-default",
    title: "All Zones Temperature Status",
    description:
      "Current temperatures across all four zones compared to their target ranges",
    icon: "thermometer",
    reasoning: "Quick overview of facility temperature health",
    spec: {
      type: "zone-health",
      timeRange: "24h",
    },
  },
  {
    id: "timeline-24h-default",
    title: "24-Hour Temperature Trends",
    description: "Temperature readings for all zones over the past 24 hours",
    icon: "clock",
    reasoning: "See how temperatures have changed over time",
    spec: {
      type: "timeline",
      timeRange: "24h",
      metrics: ["temperature"],
    },
  },
  {
    id: "activity-heatmap-default",
    title: "Facility Activity Patterns",
    description:
      "Door access and motion activity across all zones by time of day",
    icon: "activity",
    reasoning: "Understand facility usage patterns",
    spec: {
      type: "heatmap",
      metric: "door_opens",
      timeRange: "7d",
    },
  },
  {
    id: "cold-comparison-default",
    title: "Cold Storage Comparison",
    description:
      "Side-by-side comparison of Cold Room A and Cold Room B performance",
    icon: "layers",
    reasoning: "Compare cold storage zones",
    spec: {
      type: "comparison",
      zones: ["Z2", "Z3"],
    },
  },
];
