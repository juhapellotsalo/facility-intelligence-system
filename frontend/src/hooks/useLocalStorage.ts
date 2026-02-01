import { useState, useEffect, useCallback } from "react";

/**
 * Hook for persisting state in localStorage.
 * Syncs state with localStorage on change and restores on mount.
 */
export function useLocalStorage<T>(
  key: string,
  defaultValue: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  // Initialize state from localStorage or default
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key);
      if (stored !== null) {
        return JSON.parse(stored) as T;
      }
    } catch {
      // Invalid JSON or localStorage error - use default
    }
    return defaultValue;
  });

  // Persist to localStorage when value changes
  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // localStorage full or unavailable - ignore
    }
  }, [key, value]);

  // Wrapper that matches useState signature
  const setPersistedValue = useCallback((newValue: T | ((prev: T) => T)) => {
    setValue(newValue);
  }, []);

  return [value, setPersistedValue];
}
