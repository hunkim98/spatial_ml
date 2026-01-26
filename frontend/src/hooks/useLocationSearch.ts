import { useState, useCallback } from "react";
import axios from "axios";
import { Corner } from "@/types/db";

interface SearchResult {
  displayName: string;
  lat: number;
  lon: number;
  boundingBox: [number, number, number, number]; // [south, north, west, east]
}

/**
 * Hook for searching locations using Nominatim (OpenStreetMap geocoder).
 * Free, no API key required.
 */
export function useLocationSearch() {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (query: string) => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Nominatim free geocoding API
      const response = await axios.get(
        "https://nominatim.openstreetmap.org/search",
        {
          params: {
            q: query,
            format: "json",
            addressdetails: 1,
            limit: 5,
            countrycodes: "us", // Limit to US for state/county search
          },
          headers: {
            "User-Agent": "SpatialML/1.0", // Required by Nominatim
          },
        }
      );

      const mapped: SearchResult[] = response.data.map((item: any) => ({
        displayName: item.display_name,
        lat: parseFloat(item.lat),
        lon: parseFloat(item.lon),
        boundingBox: item.boundingbox.map(parseFloat),
      }));

      setResults(mapped);
    } catch (err) {
      setError("Search failed");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setResults([]);
    setError(null);
  }, []);

  return { results, loading, error, search, clear };
}
