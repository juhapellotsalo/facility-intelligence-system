import { useState, useCallback } from "react";
import { Topbar } from "./components/layout/Topbar";
import type { CanvasView } from "./components/layout/CanvasTabs";
import { BlueprintView } from "./components/blueprint/BlueprintView";
import {
  AssistantPanel,
  type AssistantPanelHandle,
} from "./components/panel/AssistantPanel";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ViewportGuard } from "./components/ViewportGuard";
import { useLocalStorage } from "./hooks/useLocalStorage";
import { useVisualizationCache } from "./hooks/useVisualizationCache";
import { VisualizeView } from "./components/visualizations/VisualizeView";
import type { VisualizationIdea } from "./components/visualizations/VisualizationIdeas";
import { DEFAULT_IDEAS } from "./components/visualizations/sampleIdeas";
import {
  type VisualizationSpec,
  type VisualizationIdea as ApiVisualizationIdea,
} from "./lib/api";

const MIN_PANEL_WIDTH = 320;
const MAX_PANEL_WIDTH = 900;
const DEFAULT_PANEL_WIDTH = 520;

function App() {
  const [panelWidth, setPanelWidth] = useLocalStorage(
    "facility-assistant-panel-width",
    DEFAULT_PANEL_WIDTH,
  );
  const [assistantHandle, setAssistantHandle] =
    useState<AssistantPanelHandle | null>(null);
  const [canvasView, setCanvasView] = useLocalStorage<CanvasView>(
    "facility-canvas-view",
    "blueprint",
  );

  // Single session ID shared across chat and visualization
  const [sessionId] = useState(() => `session-${Date.now()}`);

  // Visualization state with caching
  const { cache, setSelectedId } = useVisualizationCache(sessionId);
  const [isLoadingViz, setIsLoadingViz] = useState(false);
  const [vizSpec, setVizSpec] = useState<VisualizationSpec | null>(null);
  const [vizError, setVizError] = useState<string | null>(null);

  // Always use hardcoded DEFAULT_IDEAS for the viz view
  const selectedIdea =
    DEFAULT_IDEAS.find((i) => i.id === cache?.selectedIdeaId) ?? null;

  const handlePanelResize = useCallback(
    (delta: number) => {
      setPanelWidth((prev) => {
        const newWidth = prev - delta;
        return Math.max(MIN_PANEL_WIDTH, Math.min(MAX_PANEL_WIDTH, newWidth));
      });
    },
    [setPanelWidth],
  );

  const handleAskAssistant = useCallback(
    (query: string) => {
      assistantHandle?.sendQuery(query);
    },
    [assistantHandle],
  );

  // Handle view change
  const handleViewChange = useCallback(
    (view: CanvasView) => {
      setCanvasView(view);
    },
    [setCanvasView],
  );

  // Handle visualization ready callback from assistant
  const handleVisualizationReady = useCallback(
    (spec: VisualizationSpec, _ideaId: string, title: string) => {
      console.log("Received visualization:", title, spec);
      setVizSpec(spec);
      setIsLoadingViz(false);
    },
    [],
  );

  // Handle idea selection and visualization generation
  const handleSelectIdea = useCallback(
    async (idea: VisualizationIdea) => {
      setSelectedId(idea.id);
      setVizError(null);

      // Generate visualization through the assistant panel
      setIsLoadingViz(true);
      setVizSpec(null);

      // Convert to API idea format and send through assistant
      const apiIdea: ApiVisualizationIdea = {
        id: idea.id,
        title: idea.title,
        description: idea.description,
        icon: idea.icon,
        reasoning: idea.reasoning,
        spec: idea.spec || {},
      };

      // Route through assistant - it will call handleVisualizationReady when done
      await assistantHandle?.sendVisualizationRequest(apiIdea);
    },
    [setSelectedId, assistantHandle],
  );

  // Handle clear selection - go back to ideas grid
  const handleClearSelection = useCallback(() => {
    setSelectedId(null);
    setVizSpec(null);
    setVizError(null);
  }, [setSelectedId]);

  // Handle focus chat - focus the assistant input
  const handleFocusChat = useCallback(() => {
    assistantHandle?.focusInput();
  }, [assistantHandle]);

  return (
    <ViewportGuard>
      <div
        className="grid h-screen grid-rows-[48px_1fr]"
        style={{
          gridTemplateColumns: `1fr ${panelWidth}px`,
        }}
      >
        <Topbar activeView={canvasView} onViewChange={handleViewChange} />
        <main className="flex flex-col overflow-hidden bg-bg-base">
          {/* Canvas Content */}
          <div className="min-h-0 flex-1 overflow-auto">
            <ErrorBoundary fallbackTitle="View failed to load">
              {canvasView === "blueprint" && (
                <div className="h-full overflow-auto p-4">
                  <BlueprintView onAskAssistant={handleAskAssistant} />
                </div>
              )}

              {canvasView === "visualize" && (
                <VisualizeView
                  ideas={DEFAULT_IDEAS}
                  selectedIdea={selectedIdea}
                  onSelectIdea={handleSelectIdea}
                  onFocusChat={handleFocusChat}
                  onClearSelection={handleClearSelection}
                  isLoadingViz={isLoadingViz}
                  vizSpec={vizSpec}
                  vizError={vizError}
                />
              )}
            </ErrorBoundary>
          </div>
        </main>
        <ErrorBoundary fallbackTitle="Assistant failed to load">
          <AssistantPanel
            sessionId={sessionId}
            onResize={handlePanelResize}
            onReady={setAssistantHandle}
            onVisualizationReady={handleVisualizationReady}
          />
        </ErrorBoundary>
      </div>
    </ViewportGuard>
  );
}

export default App;
