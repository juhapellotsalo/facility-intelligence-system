import { useQuery } from "@tanstack/react-query";
import { fetchSensors } from "../lib/api";
import type { SensorConfig } from "../data/sensors";

export function useSensors() {
  return useQuery<SensorConfig[]>({
    queryKey: ["sensors"],
    queryFn: fetchSensors,
  });
}
