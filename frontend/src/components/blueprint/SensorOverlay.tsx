import { useEffect, useRef, useState, useCallback } from "react";
import { X } from "lucide-react";
import type { SensorConfig } from "../../data/sensors";
import type { SensorStatus } from "../../types";

interface SensorOverlayProps {
  sensor: SensorConfig;
  anchorId: string;
  onClose: () => void;
  onAskAssistant?: (query: string) => void;
}

const STATUS_COLORS: Record<SensorStatus, string> = {
  normal: "#73bf69",
  warning: "#fade2a",
  critical: "#ff4444",
};

const STATUS_BADGE_CLASSES: Record<SensorStatus, string> = {
  normal: "bg-status-normal-bg text-status-normal",
  warning: "bg-status-warning-bg text-status-warning",
  critical: "bg-status-critical-bg text-status-critical",
};

function Sparkline({
  data,
  color,
  width = 240,
  height = 48,
}: {
  data: number[];
  color: string;
  width?: number;
  height?: number;
}) {
  if (data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pad = 2;

  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = pad + (1 - (v - min) / range) * (height - pad * 2);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="block"
    >
      <rect width={width} height={height} rx={4} fill="rgba(0,0,0,0.25)" />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function SensorOverlay({
  sensor,
  anchorId,
  onClose,
  onAskAssistant,
}: SensorOverlayProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  const calcPosition = useCallback(() => {
    const anchor = document.getElementById(anchorId);
    if (!anchor) return;

    const rect = anchor.getBoundingClientRect();
    const overlayW = 288;
    const overlayH = 320;
    const gap = 8;

    let top: number;
    let left: number;

    // Vertical: prefer below, fall back to above
    if (rect.bottom + gap + overlayH <= window.innerHeight) {
      top = rect.bottom + gap;
    } else {
      top = rect.top - gap - overlayH;
    }

    // Horizontal: center on anchor, clamp to viewport
    left = rect.left + rect.width / 2 - overlayW / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - overlayW - 8));

    // Clamp top too
    top = Math.max(8, Math.min(top, window.innerHeight - overlayH - 8));

    setPos({ top, left });
  }, [anchorId]);

  useEffect(() => {
    calcPosition();
  }, [calcPosition]);

  // Click-outside dismiss
  useEffect(() => {
    function handleMouseDown(e: MouseEvent) {
      const target = e.target as HTMLElement;
      if (
        overlayRef.current &&
        !overlayRef.current.contains(target) &&
        !target.closest(`#${anchorId}`)
      ) {
        onClose();
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [anchorId, onClose]);

  if (!pos) return null;

  const { reading, stats, trend } = sensor;
  const color = STATUS_COLORS[reading.status];

  return (
    <div
      ref={overlayRef}
      className="fixed z-50 w-[288px] rounded-lg border border-bg-border bg-bg-surface shadow-2xl shadow-black/40"
      style={{ top: pos.top, left: pos.left }}
    >
      {/* Header */}
      <div className="flex items-start justify-between border-b border-bg-border px-4 pt-3 pb-2">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
            {sensor.zone}
          </div>
          <div className="text-sm font-medium text-text-primary">
            {sensor.label}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="mt-0.5 rounded p-0.5 text-text-muted transition-colors hover:bg-bg-hover hover:text-text-primary"
        >
          <X size={14} />
        </button>
      </div>

      {/* Current reading */}
      <div className="flex items-center justify-between border-b border-bg-border px-4 py-2.5">
        <span className="font-mono text-lg font-semibold text-text-primary">
          {reading.value}
          {reading.unit && (
            <span className="ml-1 text-sm text-text-muted">{reading.unit}</span>
          )}
        </span>
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${STATUS_BADGE_CLASSES[reading.status]}`}
        >
          {reading.status === "normal"
            ? "OK"
            : reading.status === "warning"
              ? "\u26A0 WRN"
              : "\u2716 CRIT"}
        </span>
      </div>

      {/* Sparkline */}
      <div className="border-b border-bg-border px-4 py-3">
        <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
          24h Trend
        </div>
        <Sparkline data={trend} color={color} />
      </div>

      {/* Stats */}
      <div className="flex gap-4 border-b border-bg-border px-4 py-2.5">
        <StatItem label="Min" value={stats.min} unit={stats.unit} />
        <StatItem label="Max" value={stats.max} unit={stats.unit} />
        <StatItem label="Avg" value={stats.avg} unit={stats.unit} />
      </div>

      {/* Actions */}
      <div className="flex gap-2 px-4 py-3">
        <button
          type="button"
          onClick={() => {
            const query =
              reading.status === "normal"
                ? `How is ${sensor.zone} ${sensor.label} doing?`
                : `Why is ${sensor.zone} ${sensor.label} at ${reading.value}${reading.unit ?? ""}?`;
            onAskAssistant?.(query);
            onClose();
          }}
          className="rounded border border-bg-border px-3 py-1.5 text-xs font-medium text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary"
        >
          {reading.status === "normal" ? "Explain" : "Explain Warning"}
        </button>
      </div>
    </div>
  );
}

function StatItem({
  label,
  value,
  unit,
}: {
  label: string;
  value: number;
  unit: string;
}) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
        {label}
      </span>
      <span className="font-mono text-xs text-text-secondary">
        {value}
        <span className="ml-0.5 text-text-muted">{unit}</span>
      </span>
    </div>
  );
}
