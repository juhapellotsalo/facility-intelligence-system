import { useState, useEffect, useCallback } from "react";
import type { VisualizationIdea } from "../components/visualizations/VisualizationIdeas";

interface VisualizationCache {
  ideas: VisualizationIdea[];
  selectedIdeaId: string | null;
  generatedAt: number;
}

interface UseVisualizationCacheReturn {
  cache: VisualizationCache | null;
  setIdeas: (ideas: VisualizationIdea[]) => void;
  setSelectedId: (id: string | null) => void;
  clearCache: () => void;
}

const CACHE_KEY_PREFIX = "facility-viz-";

/**
 * Hook for caching visualization ideas and selection in localStorage.
 * Persists ideas so switching between Blueprint and Visualize tabs is instant.
 */
export function useVisualizationCache(
  sessionId: string,
): UseVisualizationCacheReturn {
  const cacheKey = `${CACHE_KEY_PREFIX}${sessionId}`;

  const [cache, setCache] = useState<VisualizationCache | null>(() => {
    try {
      const stored = localStorage.getItem(cacheKey);
      if (stored !== null) {
        return JSON.parse(stored) as VisualizationCache;
      }
    } catch {
      // Invalid JSON or localStorage error
    }
    return null;
  });

  // Persist to localStorage when cache changes
  useEffect(() => {
    if (cache === null) {
      try {
        localStorage.removeItem(cacheKey);
      } catch {
        // localStorage unavailable
      }
    } else {
      try {
        localStorage.setItem(cacheKey, JSON.stringify(cache));
      } catch {
        // localStorage full or unavailable
      }
    }
  }, [cacheKey, cache]);

  const setIdeas = useCallback((ideas: VisualizationIdea[]) => {
    setCache({
      ideas,
      selectedIdeaId: null,
      generatedAt: Date.now(),
    });
  }, []);

  const setSelectedId = useCallback((id: string | null) => {
    setCache((prev) => {
      if (!prev) {
        // Create cache if it doesn't exist (for DEFAULT_IDEAS case)
        return {
          ideas: [],
          selectedIdeaId: id,
          generatedAt: Date.now(),
        };
      }
      return { ...prev, selectedIdeaId: id };
    });
  }, []);

  const clearCache = useCallback(() => {
    setCache(null);
  }, []);

  return { cache, setIdeas, setSelectedId, clearCache };
}
