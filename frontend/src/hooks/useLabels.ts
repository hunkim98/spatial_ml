import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { GeoLabel, SkippedLabel } from "@/types/labels";
import { uploadClippedImage } from "@/lib/storage";

interface SaveLabelParams {
  pdfHash: string;
  pdfPath: string;
  corners: GeoLabel["corners"];
  clipRect: { x: number; y: number; width: number; height: number };
  pageNumber: number;
  clippedImageBuffer: HTMLCanvasElement;
}

interface UseLabelsReturn {
  labels: Record<string, GeoLabel>;
  skippedLabels: Record<string, SkippedLabel>;
  loading: boolean;
  saveLabel: (params: SaveLabelParams) => Promise<boolean>;
  deleteLabel: (pdfHash: string) => Promise<boolean>;
  skipLabel: (pdfHash: string, pdfPath: string) => Promise<boolean>;
}

export function useLabels(): UseLabelsReturn {
  const [labels, setLabels] = useState<Record<string, GeoLabel>>({});
  const [skippedLabels, setSkippedLabels] = useState<
    Record<string, SkippedLabel>
  >({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      axios.get<Record<string, GeoLabel>>("/api/labels"),
      axios.get<Record<string, SkippedLabel>>("/api/skipped-labels"),
    ])
      .then(([labelsRes, skippedRes]) => {
        setLabels(labelsRes.data);
        setSkippedLabels(skippedRes.data);
      })
      .finally(() => setLoading(false));
  }, []);

  const saveLabel = useCallback(
    async (params: SaveLabelParams): Promise<boolean> => {
      try {
        const clippedImageUrl = await uploadClippedImage(
          params.pdfHash,
          params.clippedImageBuffer
        );

        const label: GeoLabel = {
          pdfHash: params.pdfHash,
          pdfPath: params.pdfPath,
          corners: params.corners,
          clipRect: {
            offsetX: params.clipRect.x,
            offsetY: params.clipRect.y,
            width: params.clipRect.width,
            height: params.clipRect.height,
          },
          pageNumber: params.pageNumber,
          clippedImageUrl,
        };

        await axios.post("/api/labels", { label });
        setLabels((prev) => ({ ...prev, [params.pdfHash]: label }));
        return true;
      } catch {
        return false;
      }
    },
    []
  );

  const deleteLabel = useCallback(
    async (pdfHash: string): Promise<boolean> => {
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
    },
    []
  );

  const skipLabel = useCallback(
    async (pdfHash: string, pdfPath: string): Promise<boolean> => {
      try {
        await axios.post("/api/skipped-labels", { pdfHash, pdfPath });
        setSkippedLabels((prev) => ({
          ...prev,
          [pdfHash]: { pdfHash, pdfPath },
        }));
        return true;
      } catch {
        return false;
      }
    },
    []
  );

  return { labels, skippedLabels, loading, saveLabel, deleteLabel, skipLabel };
}
