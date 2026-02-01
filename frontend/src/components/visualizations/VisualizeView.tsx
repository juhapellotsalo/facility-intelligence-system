import { ArrowLeft } from "lucide-react";
import {
  VisualizationIdeas,
  type VisualizationIdea,
} from "./VisualizationIdeas";
import { ZoneHealthVisualization } from "./ZoneHealthVisualization";
import { LiveVisualization } from "./LiveVisualization";
import { DEFAULT_IDEAS } from "./sampleIdeas";
import type { VisualizationSpec } from "../../lib/api";

interface VisualizeViewProps {
  ideas: VisualizationIdea[];
  selectedIdea: VisualizationIdea | null;
  onSelectIdea: (idea: VisualizationIdea) => void;
  onFocusChat: () => void;
  onClearSelection: () => void;
  isLoadingViz: boolean;
  vizSpec: VisualizationSpec | null;
  vizError: string | null;
}

/**
 * Visualize view with two modes:
 * 1. Ideas mode: Shows idea cards in a grid for selection
 * 2. Visualization mode: Shows the generated visualization
 */
export function VisualizeView({
  ideas,
  selectedIdea,
  onSelectIdea,
  onFocusChat,
  onClearSelection,
  isLoadingViz,
  vizSpec,
  vizError,
}: VisualizeViewProps) {
  // Use provided ideas or fall back to defaults
  const displayIdeas = ideas.length > 0 ? ideas : DEFAULT_IDEAS;

  // Show ideas grid when no visualization ready or still generating
  const showIdeasGrid = !vizSpec || isLoadingViz;

  // Show visualization when we have a spec and not loading
  const showVisualization = selectedIdea !== null && vizSpec !== null && !isLoadingViz;

  return (
    <div className="h-full overflow-auto p-4">
      {/* Ideas grid */}
      {showIdeasGrid && (
        <VisualizationIdeas
          ideas={displayIdeas}
          selectedIdeaId={selectedIdea?.id ?? null}
          onSelectIdea={onSelectIdea}
          onFocusChat={onFocusChat}
          isGenerating={isLoadingViz}
        />
      )}

      {/* Visualization display */}
      {showVisualization && (
        <div className="space-y-4">
          {/* Back to ideas + title */}
          <div className="flex items-center gap-3">
            <button
              onClick={onClearSelection}
              className="flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary"
            >
              <ArrowLeft size={16} />
              Back to ideas
            </button>
            <div className="h-4 w-px bg-border-subtle" />
            <h2 className="text-sm font-medium text-text-primary">
              {selectedIdea.title}
            </h2>
          </div>

          {/* Visualization content */}
          <DynamicVisualization spec={vizSpec} />
        </div>
      )}

      {/* Error display - show when we have an error */}
      {vizError && !isLoadingViz && (
        <div className="flex flex-col items-center justify-center py-16">
          <p className="mb-2 text-sm text-red-400">
            Failed to generate visualization
          </p>
          <p className="text-xs text-text-muted">{vizError}</p>
          <button
            onClick={onClearSelection}
            className="mt-4 flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary"
          >
            <ArrowLeft size={16} />
            Back to ideas
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * Renders a visualization based on the spec.
 *
 * Priority:
 * 1. If spec.code exists, use LiveVisualization (AI-generated JSX)
 * 2. If spec.type matches a known type, use that component
 * 3. Fallback: show JSON for debugging
 */
function DynamicVisualization({ spec }: { spec: VisualizationSpec }) {
  // Dynamic code-based visualization (new approach)
  if (spec.code) {
    return (
      <LiveVisualization
        code={spec.code}
        data={spec.data}
        title={spec.title}
      />
    );
  }

  // Legacy type-based routing (keep for backwards compatibility)
  if (spec.type === "zone-health" && spec.data?.zones) {
    return <ZoneHealthVisualization data={spec.data} />;
  }

  // Fallback: show the spec as JSON for debugging
  return (
    <div className="rounded-lg border border-border-subtle bg-bg-surface p-4">
      <h3 className="mb-2 text-sm font-medium text-text-primary">
        {spec.title || spec.type}
      </h3>
      <pre className="overflow-auto rounded bg-bg-raised p-3 text-xs text-text-secondary">
        {JSON.stringify(spec, null, 2)}
      </pre>
    </div>
  );
}
