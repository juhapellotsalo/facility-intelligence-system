import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
} from "recharts";

export interface ChartDataPoint {
  time: string;
  value: number;
  label?: string;
}

export interface ChartSpec {
  type: "line" | "area";
  title: string;
  data: ChartDataPoint[];
  yAxisLabel?: string;
  unit?: string;
  target?: number;
  targetLabel?: string;
  color?: string;
  warningThreshold?: number;
}

interface ChatChartProps {
  chart: ChartSpec;
}

/**
 * Renders an inline chart in the chat panel.
 * Supports line and area charts for time-series data.
 */
export function ChatChart({ chart }: ChatChartProps) {
  const {
    type,
    title,
    data,
    yAxisLabel,
    unit = "",
    target,
    targetLabel,
    color = "#8b5cf6",
    warningThreshold,
  } = chart;

  const ChartComponent = type === "area" ? AreaChart : LineChart;

  // Find min/max for Y axis with padding
  const values = data.map((d) => d.value);
  const minValue = Math.min(...values, target ?? Infinity);
  const maxValue = Math.max(...values, target ?? -Infinity);
  const padding = (maxValue - minValue) * 0.15;
  const yMin = Math.floor(minValue - padding);
  const yMax = Math.ceil(maxValue + padding);

  return (
    <div className="my-2 rounded-lg border border-border-primary bg-bg-primary p-3">
      <div className="mb-2 text-sm font-medium text-text-primary">{title}</div>
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <ChartComponent
            data={data}
            margin={{ top: 5, right: 5, left: -20, bottom: 5 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--color-border-secondary)"
              opacity={0.5}
            />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
              axisLine={{ stroke: "var(--color-border-primary)" }}
              tickLine={false}
            />
            <YAxis
              domain={[yMin, yMax]}
              tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
              axisLine={{ stroke: "var(--color-border-primary)" }}
              tickLine={false}
              label={
                yAxisLabel
                  ? {
                      value: yAxisLabel,
                      angle: -90,
                      position: "insideLeft",
                      style: { fontSize: 10, fill: "var(--color-text-muted)" },
                    }
                  : undefined
              }
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--color-bg-raised)",
                border: "1px solid var(--color-border-primary)",
                borderRadius: "6px",
                fontSize: "12px",
              }}
              labelStyle={{ color: "var(--color-text-primary)" }}
              formatter={(value) => [`${value}${unit}`, yAxisLabel ?? "Value"]}
            />

            {/* Target/threshold reference line */}
            {target !== undefined && (
              <ReferenceLine
                y={target}
                stroke="var(--color-status-success)"
                strokeDasharray="5 5"
                label={{
                  value: targetLabel ?? `Target: ${target}${unit}`,
                  position: "right",
                  style: { fontSize: 9, fill: "var(--color-status-success)" },
                }}
              />
            )}

            {/* Warning threshold reference line */}
            {warningThreshold !== undefined && (
              <ReferenceLine
                y={warningThreshold}
                stroke="var(--color-status-warning)"
                strokeDasharray="3 3"
                strokeOpacity={0.7}
              />
            )}

            {/* The actual chart line/area */}
            {type === "area" ? (
              <Area
                type="monotone"
                dataKey="value"
                stroke={color}
                fill={color}
                fillOpacity={0.15}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: color }}
              />
            ) : (
              <Line
                type="monotone"
                dataKey="value"
                stroke={color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: color }}
              />
            )}
          </ChartComponent>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
