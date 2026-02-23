import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { GeoLabel } from "@/types/labels";
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
  loading: boolean;
  saveLabel: (params: SaveLabelParams) => Promise<boolean>;
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

  return { labels, loading, saveLabel, deleteLabel };
}
