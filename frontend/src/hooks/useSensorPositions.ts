import { useLocalStorage } from "./useLocalStorage";

/**
 * Sensor position as percentage of zone dimensions (0-100).
 * Using percentages ensures positions stay valid when window resizes.
 */
export interface SensorPosition {
  x: number; // percentage from left (0-100)
  y: number; // percentage from top (0-100)
}

export type SensorPositions = Record<string, SensorPosition>;

/**
 * Default positions for all sensors within their zones.
 * Positions are percentages of the zone container dimensions.
 */
const DEFAULT_POSITIONS: SensorPositions = {
  // Loading Bay - horizontal spread across the zone
  "loading-temp": { x: 10, y: 50 },
  "loading-aq": { x: 35, y: 50 },
  "loading-door": { x: 60, y: 50 },
  "loading-motion": { x: 85, y: 50 },

  // Cold Room A - vertical layout
  "cold-a-motion": { x: 50, y: 20 },
  "cold-a-temp": { x: 50, y: 70 },

  // Cold Room B - spread out
  "cold-b-door": { x: 20, y: 20 },
  "cold-b-temp": { x: 50, y: 50 },
  "cold-b-motion": { x: 80, y: 80 },

  // Dry Storage - vertical layout
  "dry-temp": { x: 50, y: 30 },
  "dry-aq": { x: 50, y: 70 },
};

const STORAGE_KEY = "facility-sensor-positions";

/**
 * Hook for managing draggable sensor positions with localStorage persistence.
 */
export function useSensorPositions() {
  const [positions, setPositions] = useLocalStorage<SensorPositions>(
    STORAGE_KEY,
    DEFAULT_POSITIONS,
  );

  /**
   * Update a single sensor's position.
   * Coordinates are clamped to 0-100 range.
   */
  const updatePosition = (sensorId: string, x: number, y: number) => {
    setPositions((prev) => ({
      ...prev,
      [sensorId]: {
        x: Math.max(0, Math.min(100, x)),
        y: Math.max(0, Math.min(100, y)),
      },
    }));
  };

  /**
   * Get position for a sensor, falling back to default if not set.
   */
  const getPosition = (sensorId: string): SensorPosition => {
    return (
      positions[sensorId] ?? DEFAULT_POSITIONS[sensorId] ?? { x: 50, y: 50 }
    );
  };

  /**
   * Reset all positions to defaults.
   */
  const resetPositions = () => {
    setPositions(DEFAULT_POSITIONS);
  };

  return {
    positions,
    getPosition,
    updatePosition,
    resetPositions,
  };
}
