import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSensorPositions } from "../useSensorPositions";

describe("useSensorPositions", () => {
  it("returns default positions on first load", () => {
    const { result } = renderHook(() => useSensorPositions());

    // Check a known default position
    const pos = result.current.getPosition("cold-b-temp");
    expect(pos).toEqual({ x: 50, y: 50 });
  });

  it("returns fallback position for unknown sensor", () => {
    const { result } = renderHook(() => useSensorPositions());

    const pos = result.current.getPosition("unknown-sensor");
    expect(pos).toEqual({ x: 50, y: 50 });
  });

  it("updates sensor position", () => {
    const { result } = renderHook(() => useSensorPositions());

    act(() => {
      result.current.updatePosition("cold-b-temp", 25, 75);
    });

    const pos = result.current.getPosition("cold-b-temp");
    expect(pos).toEqual({ x: 25, y: 75 });
  });

  it("clamps position values to 0-100 range", () => {
    const { result } = renderHook(() => useSensorPositions());

    act(() => {
      result.current.updatePosition("cold-b-temp", -10, 150);
    });

    const pos = result.current.getPosition("cold-b-temp");
    expect(pos).toEqual({ x: 0, y: 100 });
  });

  it("resets positions to defaults", () => {
    const { result } = renderHook(() => useSensorPositions());

    // Update a position
    act(() => {
      result.current.updatePosition("cold-b-temp", 10, 10);
    });
    expect(result.current.getPosition("cold-b-temp")).toEqual({ x: 10, y: 10 });

    // Reset
    act(() => {
      result.current.resetPositions();
    });
    expect(result.current.getPosition("cold-b-temp")).toEqual({ x: 50, y: 50 });
  });

  it("persists positions to localStorage", () => {
    const { result, unmount } = renderHook(() => useSensorPositions());

    act(() => {
      result.current.updatePosition("cold-b-temp", 33, 66);
    });

    unmount();

    // Re-render and check persistence
    const { result: result2 } = renderHook(() => useSensorPositions());
    expect(result2.current.getPosition("cold-b-temp")).toEqual({ x: 33, y: 66 });
  });
});
