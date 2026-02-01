import { useState, useRef, useCallback } from "react";
import {
  Thermometer,
  DoorClosed,
  DoorOpen,
  Wind,
  User,
  Radar,
} from "lucide-react";
import type { SensorType, SensorStatus } from "../../types";

interface SensorMarkerProps {
  id: string;
  sensorType: SensorType;
  status: SensorStatus;
  value: string;
  unit?: string;
  label: string;
  statusText: string;
  rawValues?: Record<string, number | string | boolean>;
  className?: string;
  onClick?: () => void;
  // Draggable positioning (percentages 0-100)
  position?: { x: number; y: number };
  onPositionChange?: (x: number, y: number) => void;
}

const STATUS_ICON_CLASSES: Record<SensorStatus, string> = {
  normal: "bg-status-normal-bg text-status-normal",
  warning: "bg-status-warning-bg text-status-warning",
  critical: "bg-status-critical-bg text-status-critical",
};

const STATUS_TEXT_CLASSES: Record<SensorStatus, string> = {
  normal: "text-status-normal",
  warning: "text-status-warning",
  critical: "text-status-critical",
};

function getSensorIcon(
  sensorType: SensorType,
  rawValues?: Record<string, number | string | boolean>,
) {
  const props = { size: 16, strokeWidth: 1.8 };
  switch (sensorType) {
    case "environmental":
      return <Thermometer {...props} />;
    case "door":
      return rawValues?.isOpen ? (
        <DoorOpen {...props} />
      ) : (
        <DoorClosed {...props} />
      );
    case "air_quality":
      return <Wind {...props} />;
    case "thermal_presence":
      return <User {...props} />;
    case "motion":
      return <Radar {...props} />;
  }
}

export function SensorMarker({
  id,
  sensorType,
  status,
  value,
  unit,
  label,
  rawValues,
  className = "",
  onClick,
  position,
  onPositionChange,
}: SensorMarkerProps) {
  const isWarning = status === "warning";
  const isCritical = status === "critical";
  const isDraggable = position !== undefined && onPositionChange !== undefined;

  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef<{
    x: number;
    y: number;
    startX: number;
    startY: number;
  } | null>(null);
  const containerRef = useRef<HTMLButtonElement>(null);
  const hasDraggedRef = useRef(false);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!isDraggable || !containerRef.current) return;

      // Only start drag if shift is held
      if (!e.shiftKey) return;

      e.preventDefault();
      e.stopPropagation();

      const parent = containerRef.current.parentElement;
      if (!parent) return;

      const parentRect = parent.getBoundingClientRect();
      hasDraggedRef.current = false;

      dragStartRef.current = {
        x: e.clientX,
        y: e.clientY,
        startX: position.x,
        startY: position.y,
      };
      setIsDragging(true);

      const handleMouseMove = (moveEvent: MouseEvent) => {
        if (!dragStartRef.current || !containerRef.current) return;

        const deltaX = moveEvent.clientX - dragStartRef.current.x;
        const deltaY = moveEvent.clientY - dragStartRef.current.y;

        // Convert pixel delta to percentage
        const deltaXPercent = (deltaX / parentRect.width) * 100;
        const deltaYPercent = (deltaY / parentRect.height) * 100;

        const newX = dragStartRef.current.startX + deltaXPercent;
        const newY = dragStartRef.current.startY + deltaYPercent;

        // Calculate bounds based on card dimensions relative to container
        const cardRect = containerRef.current.getBoundingClientRect();
        const halfWidthPercent = (cardRect.width / 2 / parentRect.width) * 100;
        const halfHeightPercent =
          (cardRect.height / 2 / parentRect.height) * 100;

        const minX = halfWidthPercent;
        const maxX = 100 - halfWidthPercent;
        const minY = halfHeightPercent;
        const maxY = 100 - halfHeightPercent;

        const clampedX = Math.max(minX, Math.min(maxX, newX));
        const clampedY = Math.max(minY, Math.min(maxY, newY));

        // Mark as dragged if moved more than 3px
        if (Math.abs(deltaX) > 3 || Math.abs(deltaY) > 3) {
          hasDraggedRef.current = true;
        }

        onPositionChange(clampedX, clampedY);
      };

      const handleMouseUp = () => {
        setIsDragging(false);
        dragStartRef.current = null;
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };

      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "grabbing";
      document.body.style.userSelect = "none";
    },
    [isDraggable, position, onPositionChange],
  );

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      // Don't trigger click if we just finished dragging
      if (hasDraggedRef.current) {
        e.preventDefault();
        e.stopPropagation();
        hasDraggedRef.current = false;
        return;
      }
      onClick?.();
    },
    [onClick],
  );

  // Position styles for draggable sensors
  const positionStyles: React.CSSProperties = isDraggable
    ? {
        position: "absolute",
        left: `${position.x}%`,
        top: `${position.y}%`,
        transform: "translate(-50%, -50%)",
        zIndex: isDragging ? 50 : 10,
      }
    : {};

  // Build tooltip text
  const tooltipText = `${label}: ${value}${unit ?? ""}${isWarning ? " (Warning)" : isCritical ? " (Critical)" : ""}`;

  // Determine what value to display based on sensor type
  // - Environmental/air quality: always show the reading
  // - Door: show "Open" only when open (closed is default, no need to show)
  // - Motion: show "Active" only when motion detected
  const getDisplayValue = (): string | null => {
    switch (sensorType) {
      case "environmental":
      case "air_quality":
        return `${value}${unit ?? ""}`;
      case "door":
        return rawValues?.isOpen ? "Open" : null;
      case "motion":
      case "thermal_presence": {
        // Check if there's motion/presence detected
        const lowerValue = value.toLowerCase();
        const hasMotion =
          lowerValue.includes("detected") ||
          lowerValue.includes("active") ||
          (lowerValue.includes("motion") && !lowerValue.includes("no"));
        return hasMotion ? "Active" : "Clear";
      }
      default:
        return null;
    }
  };

  const displayValue = getDisplayValue();

  return (
    <button
      ref={containerRef}
      id={`sensor-${id}`}
      type="button"
      onClick={handleClick}
      onMouseDown={handleMouseDown}
      title={tooltipText}
      className={`group flex items-center gap-1.5 rounded-md border bg-bg-raised/90 px-1.5 py-1 backdrop-blur-sm transition-all hover:bg-bg-hover hover:shadow-md ${
        isWarning
          ? "border-status-warning/40 animate-[warning-pulse_2s_ease-in-out_infinite]"
          : isCritical
            ? "border-status-critical/40 animate-[critical-pulse_1s_ease-in-out_infinite]"
            : "border-bg-border/50"
      } ${isDragging ? "shadow-lg ring-2 ring-cyan-400/50" : ""} ${className}`}
      style={positionStyles}
    >
      {/* Icon */}
      <div
        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded ${STATUS_ICON_CLASSES[status]}`}
      >
        {getSensorIcon(sensorType, rawValues)}
      </div>

      {/* Value - contextual based on sensor type */}
      {displayValue && (
        <span
          className={`text-xs font-medium ${
            isWarning || isCritical
              ? STATUS_TEXT_CLASSES[status]
              : "text-text-primary"
          }`}
        >
          {displayValue}
        </span>
      )}
    </button>
  );
}
