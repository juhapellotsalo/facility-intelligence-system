import type { SensorType, SensorStatus } from "../types";

/**
 * Sensor configuration types - matches backend API response shape.
 */

export interface SensorReading {
  value: string;
  unit?: string;
  status: SensorStatus;
  statusText: string;
  rawValues?: Record<string, number | string | boolean>;
}

export interface SensorStats {
  min: number;
  max: number;
  avg: number;
  unit: string;
}

export interface SensorThresholds {
  warning?: number;
  critical?: number;
}

export interface SensorConfig {
  id: string;
  sensorType: SensorType;
  zone: string;
  label: string;
  reading: SensorReading;
  trend: number[];
  stats: SensorStats;
  thresholds?: SensorThresholds;
  className?: string;
}
