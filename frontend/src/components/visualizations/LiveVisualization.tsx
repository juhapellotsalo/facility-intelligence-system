import { LiveProvider, LivePreview, LiveError } from "react-live";
import {
  // Chart types
  AreaChart,
  BarChart,
  LineChart,
  PieChart,
  ComposedChart,
  RadarChart,
  RadialBarChart,
  // Chart elements
  Area,
  Bar,
  Line,
  Pie,
  Cell,
  Scatter,
  Radar,
  RadialBar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  // Axes and grid
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  // Reference elements
  ReferenceLine,
  ReferenceArea,
  ReferenceDot,
  // Labels and legends
  Tooltip,
  Legend,
  Label,
  LabelList,
  // Container and utilities
  ResponsiveContainer,
  Brush,
  ErrorBar,
} from "recharts";

/**
 * Color palette available to generated visualizations
 */
const colors = {
  blue: "#3b82f6",
  green: "#22c55e",
  yellow: "#eab308",
  red: "#ef4444",
  purple: "#a855f7",
  orange: "#f97316",
  cyan: "#06b6d4",
  pink: "#ec4899",
  gray: "#6b7280",
  // Status colors
  normal: "#22c55e",
  warning: "#eab308",
  critical: "#ef4444",
};

/**
 * Scope of components and utilities available to generated code.
 * The AI-generated JSX can use any of these without imports.
 */
const createScope = (data: Record<string, unknown>) => ({
  // Chart types
  AreaChart,
  BarChart,
  LineChart,
  PieChart,
  ComposedChart,
  RadarChart,
  RadialBarChart,
  // Chart elements
  Area,
  Bar,
  Line,
  Pie,
  Cell,
  Scatter,
  Radar,
  RadialBar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  // Axes and grid
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  // Reference elements
  ReferenceLine,
  ReferenceArea,
  ReferenceDot,
  // Labels and legends
  Tooltip,
  Legend,
  Label,
  LabelList,
  // Container and utilities
  ResponsiveContainer,
  Brush,
  ErrorBar,

  // Data passed from the backend
  data,

  // Color palette
  colors,

  // Utility for formatting
  formatNumber: (n: number, decimals = 1) => n.toFixed(decimals),
  formatPercent: (n: number) => `${(n * 100).toFixed(0)}%`,
});

interface LiveVisualizationProps {
  /** JSX code string to render */
  code: string;
  /** Data to make available to the visualization */
  data: Record<string, unknown>;
  /** Optional title */
  title?: string;
}

/**
 * Renders AI-generated JSX code using react-live.
 *
 * The generated code has access to:
 * - All Recharts components (LineChart, BarChart, etc.)
 * - `data` object containing visualization data
 * - `colors` palette for consistent styling
 * - Formatting utilities (formatNumber, formatPercent)
 *
 * Example generated code:
 * ```jsx
 * <ResponsiveContainer width="100%" height={300}>
 *   <LineChart data={data.readings}>
 *     <XAxis dataKey="time" />
 *     <YAxis />
 *     <Line type="monotone" dataKey="value" stroke={colors.blue} />
 *   </LineChart>
 * </ResponsiveContainer>
 * ```
 */
export function LiveVisualization({
  code,
  data,
  title,
}: LiveVisualizationProps) {
  const scope = createScope(data);

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border-subtle bg-bg-surface p-4">
        {title && (
          <h3 className="mb-4 text-sm font-medium text-text-primary">
            {title}
          </h3>
        )}

        <LiveProvider code={code} scope={scope} noInline={false}>
          <div className="min-h-[200px]">
            <LivePreview />
          </div>
          <LiveError className="mt-2 rounded bg-red-500/10 p-3 text-xs text-red-400" />
        </LiveProvider>
      </div>

    </div>
  );
}
