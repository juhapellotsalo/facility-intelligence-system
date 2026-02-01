import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useLocalStorage } from "../useLocalStorage";

describe("useLocalStorage", () => {
  it("returns default value when localStorage is empty", () => {
    const { result } = renderHook(() => useLocalStorage("test-key", "default"));
    expect(result.current[0]).toBe("default");
  });

  it("persists value to localStorage", () => {
    const { result } = renderHook(() => useLocalStorage("test-key", "default"));

    act(() => {
      result.current[1]("new value");
    });

    expect(result.current[0]).toBe("new value");
    expect(localStorage.getItem("test-key")).toBe('"new value"');
  });

  it("reads existing value from localStorage", () => {
    localStorage.setItem("existing-key", JSON.stringify("stored value"));

    const { result } = renderHook(() =>
      useLocalStorage("existing-key", "default"),
    );

    expect(result.current[0]).toBe("stored value");
  });

  it("supports functional updates", () => {
    const { result } = renderHook(() => useLocalStorage("counter", 0));

    act(() => {
      result.current[1]((prev) => prev + 1);
    });

    expect(result.current[0]).toBe(1);

    act(() => {
      result.current[1]((prev) => prev + 5);
    });

    expect(result.current[0]).toBe(6);
  });

  it("handles objects correctly", () => {
    const defaultObj = { name: "test", count: 0 };
    const { result } = renderHook(() => useLocalStorage("obj-key", defaultObj));

    act(() => {
      result.current[1]({ name: "updated", count: 42 });
    });

    expect(result.current[0]).toEqual({ name: "updated", count: 42 });
    expect(JSON.parse(localStorage.getItem("obj-key") ?? "{}")).toEqual({
      name: "updated",
      count: 42,
    });
  });
});
