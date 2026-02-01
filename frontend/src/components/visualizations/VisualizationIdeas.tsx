import {
  BarChart3,
  Clock,
  Thermometer,
  Activity,
  TrendingUp,
  Grid3X3,
  MessageSquare,
} from "lucide-react";

export interface VisualizationIdea {
  id: string;
  title: string;
  description: string;
  icon: string;
  reasoning: string;
  spec?: Record<string, unknown>;
}

interface VisualizationIdeasProps {
  ideas: VisualizationIdea[];
  selectedIdeaId: string | null;
  onSelectIdea: (idea: VisualizationIdea) => void;
  onFocusChat?: () => void;
  isLoading?: boolean;
  /** True when a visualization is being generated */
  isGenerating?: boolean;
}

const ICONS: Record<string, typeof BarChart3> = {
  "bar-chart": BarChart3,
  clock: Clock,
  thermometer: Thermometer,
  activity: Activity,
  trending: TrendingUp,
  grid: Grid3X3,
  layers: Grid3X3,
  zap: Activity,
};

/**
 * Grid of visualization idea cards with full content display.
 * Shows title, description, and reasoning for each idea.
 */
export function VisualizationIdeas({
  ideas,
  selectedIdeaId,
  onSelectIdea,
  onFocusChat,
  isLoading,
  isGenerating,
}: VisualizationIdeasProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="mb-4 h-6 w-6 animate-spin rounded-full border-2 border-accent-blue border-t-transparent" />
        <p className="text-sm text-text-muted">Analyzing conversation...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <p className="text-sm text-text-secondary">
        Select a visualization to explore your facility data:
      </p>

      {/* Ideas grid */}
      <div className="grid gap-3 md:grid-cols-2">
        {ideas.map((idea) => {
          const Icon = ICONS[idea.icon] || BarChart3;
          const isSelected = idea.id === selectedIdeaId;
          const isThisGenerating = isSelected && isGenerating;
          const isDisabled = isGenerating;
          return (
            <button
              key={idea.id}
              onClick={() => !isDisabled && onSelectIdea(idea)}
              disabled={isDisabled}
              className={`group flex flex-col rounded-xl border p-4 text-left transition-all ${
                isSelected
                  ? "border-accent-blue bg-accent-blue/10"
                  : isDisabled
                    ? "cursor-not-allowed border-border-subtle bg-bg-surface opacity-50"
                    : "border-border-subtle bg-bg-surface hover:border-accent-blue/50 hover:bg-bg-raised"
              }`}
            >
              <div className="mb-3 flex items-center gap-2">
                <div
                  className={`rounded-lg p-1.5 ${
                    isSelected
                      ? "bg-accent-blue/20 text-accent-blue"
                      : "bg-bg-raised text-accent-blue group-hover:bg-accent-blue/10"
                  }`}
                >
                  {isThisGenerating ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent-blue border-t-transparent" />
                  ) : (
                    <Icon size={16} />
                  )}
                </div>
                <h3
                  className={`font-semibold ${
                    isSelected ? "text-accent-blue" : "text-text-primary"
                  }`}
                >
                  {idea.title}
                </h3>
                {isThisGenerating && (
                  <span className="text-xs text-text-muted">Generating...</span>
                )}
              </div>
              <p className="text-sm text-text-secondary">
                "{idea.description}"
              </p>
            </button>
          );
        })}
      </div>

      {/* Custom visualization prompt */}
      <div
        className={`flex items-center justify-center gap-2 rounded-lg border border-dashed border-border-subtle py-3 text-sm text-text-muted ${isGenerating ? "opacity-50" : ""}`}
      >
        <MessageSquare size={16} />
        <button
          onClick={onFocusChat}
          disabled={isGenerating}
          className="font-medium text-accent-blue hover:underline disabled:cursor-not-allowed disabled:text-text-muted disabled:no-underline"
        >
          Or tell the assistant what you'd like to see →
        </button>
      </div>
    </div>
  );
}
