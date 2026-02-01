import { MapPin, BarChart3 } from "lucide-react";

export type CanvasView = "blueprint" | "visualize";

interface CanvasTabsProps {
  activeView: CanvasView;
  onViewChange: (view: CanvasView) => void;
}

/**
 * Tab toggle for switching between Blueprint and Visualize views.
 */
export function CanvasTabs({ activeView, onViewChange }: CanvasTabsProps) {
  return (
    <div className="flex items-center gap-1 rounded-lg bg-bg-raised p-1">
      <button
        onClick={() => onViewChange("blueprint")}
        className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
          activeView === "blueprint"
            ? "bg-bg-surface text-text-primary shadow-sm"
            : "text-text-secondary hover:text-text-primary"
        }`}
      >
        <MapPin size={16} />
        Floor Plan
      </button>
      <button
        onClick={() => onViewChange("visualize")}
        className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
          activeView === "visualize"
            ? "bg-bg-surface text-text-primary shadow-sm"
            : "text-text-secondary hover:text-text-primary"
        }`}
      >
        <BarChart3 size={16} />
        Visualize
      </button>
    </div>
  );
}
