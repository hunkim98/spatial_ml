import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { GeoLabel } from "@/types/db";

interface UseLabelsReturn {
  labels: Record<string, GeoLabel>;
  loading: boolean;
  saveLabel: (label: GeoLabel) => Promise<boolean>;
  deleteLabel: (pdfHash: string) => Promise<boolean>;
}

export function useLabels(): UseLabelsReturn {
  const [labels, setLabels] = useState<Record<string, GeoLabel>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios
      .get<Record<string, GeoLabel>>("/api/labels")
      .then((res) => setLabels(res.data))
      .finally(() => setLoading(false));
  }, []);

  const saveLabel = useCallback(async (label: GeoLabel): Promise<boolean> => {
    try {
      await axios.post("/api/labels", label);
      setLabels((prev) => ({ ...prev, [label.pdfHash]: label }));
      return true;
    } catch {
      return false;
    }
  }, []);

  const deleteLabel = useCallback(async (pdfHash: string): Promise<boolean> => {
    try {
      await axios.delete("/api/labels", { data: { pdfHash } });
      setLabels((prev) => {
        const next = { ...prev };
        delete next[pdfHash];
        return next;
      });
      return true;
    } catch {
      return false;
    }
  }, []);

  return { labels, loading, saveLabel, deleteLabel };
}
