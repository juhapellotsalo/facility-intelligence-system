import { useState, useCallback, useMemo } from "react";
import { SensorMarker } from "./SensorMarker";
import { SensorOverlay } from "./SensorOverlay";
import { useSensorPositions } from "../../hooks/useSensorPositions";
import { useSensors } from "../../hooks/useSensors";
import type { SensorConfig } from "../../data/sensors";

/** Zone name patterns to grid area mapping */
const ZONE_PATTERNS: Record<string, (zone: string) => boolean> = {
  loading: (zone) => zone.toLowerCase().includes("loading"),
  coldA: (zone) => zone.toLowerCase().includes("cold room a"),
  coldB: (zone) => zone.toLowerCase().includes("cold room b"),
  dry: (zone) => zone.toLowerCase().includes("dry"),
};

interface SensorFromDataProps {
  sensor: SensorConfig;
  onClick: (id: string) => void;
  position: { x: number; y: number };
  onPositionChange: (x: number, y: number) => void;
}

function SensorFromData({
  sensor,
  onClick,
  position,
  onPositionChange,
}: SensorFromDataProps) {
  return (
    <SensorMarker
      id={sensor.id}
      sensorType={sensor.sensorType}
      status={sensor.reading.status}
      value={sensor.reading.value}
      unit={sensor.reading.unit}
      label={sensor.label}
      statusText={sensor.reading.statusText}
      rawValues={sensor.reading.rawValues}
      onClick={() => onClick(sensor.id)}
      position={position}
      onPositionChange={onPositionChange}
    />
  );
}

interface BlueprintViewProps {
  onAskAssistant?: (query: string) => void;
}

export function BlueprintView({ onAskAssistant }: BlueprintViewProps) {
  const [selectedSensorId, setSelectedSensorId] = useState<string | null>(null);
  const { getPosition, updatePosition } = useSensorPositions();
  const { data: sensors, isLoading, error } = useSensors();

  // Create a lookup map for sensors by ID
  const sensorMap = useMemo(() => {
    if (!sensors) return new Map<string, SensorConfig>();
    return new Map(sensors.map((s) => [s.id, s]));
  }, [sensors]);

  // Group sensors by zone area
  const sensorsByZone = useMemo(() => {
    if (!sensors) return { loading: [], coldA: [], coldB: [], dry: [] };
    return {
      loading: sensors.filter((s) => ZONE_PATTERNS.loading(s.zone)),
      coldA: sensors.filter((s) => ZONE_PATTERNS.coldA(s.zone)),
      coldB: sensors.filter((s) => ZONE_PATTERNS.coldB(s.zone)),
      dry: sensors.filter((s) => ZONE_PATTERNS.dry(s.zone)),
    };
  }, [sensors]);

  const handleSensorClick = useCallback((id: string) => {
    setSelectedSensorId((prev) => (prev === id ? null : id));
  }, []);

  const handleOverlayClose = useCallback(() => {
    setSelectedSensorId(null);
  }, []);

  // Create position change handler for a specific sensor
  const makePositionHandler = useCallback(
    (sensorId: string) => (x: number, y: number) => {
      updatePosition(sensorId, x, y);
    },
    [updatePosition],
  );

  const selectedSensor = selectedSensorId
    ? (sensorMap.get(selectedSensorId) ?? null)
    : null;

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-text-muted">
        Loading sensors...
      </div>
    );
  }

  if (error) {
    throw error; // Let ErrorBoundary handle this
  }

  return (
    <div className="blueprint-grid relative h-full p-5 pb-9">
      {/* Building — connected floor plan */}
      <div
        className="relative grid h-full"
        style={{
          gridTemplateColumns: "1fr 1.4fr 0.9fr",
          gridTemplateRows: "0.7fr 1.3fr",
          gridTemplateAreas: `"loading loading loading" "cold-a cold-b dry"`,
        }}
      >
        {/* ===== LOADING BAY ===== */}
        <div
          className="relative border border-bg-border bg-bg-surface p-4 transition-colors hover:bg-bg-raised"
          style={{
            gridArea: "loading",
            borderTopWidth: 2,
            borderTopColor: "rgba(255, 152, 48, 0.25)",
            background:
              "linear-gradient(180deg, var(--color-bg-surface), rgba(255, 152, 48, 0.03))",
          }}
        >
          <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-secondary">
            Loading Bay
          </div>

          <DockEntrance />

          {/* Sensor container - relative for absolute positioned sensors */}
          <div className="relative h-[calc(100%-24px)]">
            {sensorsByZone.loading.map((sensor) => (
              <SensorFromData
                key={sensor.id}
                sensor={sensor}
                onClick={handleSensorClick}
                position={getPosition(sensor.id)}
                onPositionChange={makePositionHandler(sensor.id)}
              />
            ))}
          </div>
        </div>

        {/* ===== COLD ROOM A — FRESH ===== */}
        <div
          className="relative border-2 bg-bg-surface p-4 transition-colors hover:bg-bg-raised"
          style={{
            gridArea: "cold-a",
            borderColor: "rgba(110, 200, 224, 0.2)",
            background:
              "linear-gradient(135deg, var(--color-bg-surface), rgba(110, 200, 224, 0.04))",
          }}
        >
          <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-secondary">
            Cold Room A — Fresh
          </div>
          <div className="relative h-[calc(100%-24px)]">
            {sensorsByZone.coldA.map((sensor) => (
              <SensorFromData
                key={sensor.id}
                sensor={sensor}
                onClick={handleSensorClick}
                position={getPosition(sensor.id)}
                onPositionChange={makePositionHandler(sensor.id)}
              />
            ))}
          </div>
        </div>

        {/* ===== COLD ROOM B — FROZEN ===== */}
        <div
          className="relative border-2 bg-bg-surface p-4 transition-colors hover:bg-bg-raised"
          style={{
            gridArea: "cold-b",
            borderColor: "rgba(110, 200, 224, 0.25)",
            background:
              "linear-gradient(135deg, var(--color-bg-surface), rgba(110, 200, 224, 0.05))",
          }}
        >
          <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-secondary">
            Cold Room B — Frozen
          </div>
          <div className="relative h-[calc(100%-24px)]">
            {sensorsByZone.coldB.map((sensor) => (
              <SensorFromData
                key={sensor.id}
                sensor={sensor}
                onClick={handleSensorClick}
                position={getPosition(sensor.id)}
                onPositionChange={makePositionHandler(sensor.id)}
              />
            ))}
          </div>
        </div>

        {/* ===== DRY STORAGE ===== */}
        <div
          className="relative border border-bg-surface bg-bg-surface p-4 transition-colors hover:bg-bg-raised"
          style={{
            gridArea: "dry",
            borderColor: "rgba(87, 148, 242, 0.15)",
            background:
              "linear-gradient(135deg, var(--color-bg-surface), rgba(87, 148, 242, 0.03))",
          }}
        >
          <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-secondary">
            Dry Storage
          </div>
          <div className="relative h-[calc(100%-24px)]">
            {sensorsByZone.dry.map((sensor) => (
              <SensorFromData
                key={sensor.id}
                sensor={sensor}
                onClick={handleSensorClick}
                position={getPosition(sensor.id)}
                onPositionChange={makePositionHandler(sensor.id)}
              />
            ))}
          </div>
        </div>

        {/* Door gap indicators on internal walls */}
        <DoorGap
          label="Passage"
          style={{
            top: "35%",
            left: "15%",
            transform: "translate(-50%, -50%)",
          }}
        />
        <DoorGap
          label="Freezer entry"
          style={{
            top: "35%",
            left: "42%",
            transform: "translate(-50%, -50%)",
          }}
        />
      </div>

      {/* Scale bar */}
      <div className="absolute bottom-3 left-5 flex select-none items-center gap-1.5 text-[9px] font-medium tracking-wide text-accent-blue/25">
        <div className="relative h-px w-[60px] bg-accent-blue/20">
          <div className="absolute -top-[3px] left-0 h-1.5 w-px bg-accent-blue/20" />
          <div className="absolute -top-[3px] right-0 h-1.5 w-px bg-accent-blue/20" />
        </div>
        <span>~10 m</span>
      </div>

      {/* Compass */}
      <div className="absolute bottom-2 right-3 flex select-none flex-col items-center gap-px text-[9px] font-semibold tracking-wide text-accent-blue/30">
        <span className="text-xs leading-none">&#9650;</span>
        <span>N</span>
      </div>

      {/* Sensor overlay */}
      {selectedSensor && (
        <SensorOverlay
          sensor={selectedSensor}
          anchorId={`sensor-${selectedSensor.id}`}
          onClose={handleOverlayClose}
          onAskAssistant={onAskAssistant}
        />
      )}
    </div>
  );
}

/** Dock entrance indicator on exterior top wall */
function DockEntrance() {
  return (
    <div className="absolute -top-3.5 right-[6%] z-10 flex items-center gap-2">
      <span className="text-xs text-accent-orange/60">&#9660;</span>
      <div className="relative h-px w-20 border-t-2 border-dashed border-accent-orange/50">
        <div className="absolute -top-1.5 left-[-1px] h-3 w-0.5 bg-accent-orange/50" />
        <div className="absolute -top-1.5 right-[-1px] h-3 w-0.5 bg-accent-orange/50" />
      </div>
      <span className="text-[11px] font-semibold uppercase tracking-wider text-accent-orange/70">
        Dock
      </span>
    </div>
  );
}

/** Door gap indicator on internal walls */
function DoorGap({
  label,
  style,
}: {
  label: string;
  style: React.CSSProperties;
}) {
  return (
    <div className="absolute z-[3] flex flex-col items-center" style={style}>
      <div className="relative h-px w-16 border-t-2 border-dashed border-white/25">
        <div className="absolute -top-[5px] left-[-1px] h-2.5 w-0.5 bg-white/30" />
        <div className="absolute -top-[5px] right-[-1px] h-2.5 w-0.5 bg-white/30" />
      </div>
      <span className="mt-1 text-[11px] font-medium uppercase tracking-wider text-text-muted">
        {label}
      </span>
    </div>
  );
}
