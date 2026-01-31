import { GeoCorners } from "@/canvas/overlay/types";
import { Corner } from "@/types/db";
import { forwardRef } from "react";
import { CornersChangeHandler } from "../GeoReferencer";

interface OverlayEditorComponentProps {
  pdfUrl: string;
  pageNumber: number;
}

export interface OverlayEditorComponentHandle {
  flyTo: (center: Corner, zoom?: number) => void;
  fitBounds: (bounds: [number, number, number, number]) => void;
  getCorners: () => GeoCorners | null;
  addCornersChangeListener: (listener: CornersChangeHandler) => void;
  removeCornersChangeListener: (listener: CornersChangeHandler) => void;
}

export const OverlayEditorComponent = forwardRef<
  OverlayEditorComponentHandle,
  OverlayEditorComponentProps
>(function OverlayEditorComponent({ pdfUrl, pageNumber }, ref) {
  return <div>OverlayEditorComponent</div>;
});
