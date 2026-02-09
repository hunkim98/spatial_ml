import { GeoCorners } from "@/canvas/overlay/types";
import { Corner } from "@/types/db";
import { forwardRef, useRef } from "react";
import { CornersChangeHandler } from "../GeoReferencer";
import { useOverlayEditor } from "@/hooks/useOverlayEditor";

interface OverlayEditorComponentProps {
  imageBuffer: HTMLCanvasElement;
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
>(function OverlayEditorComponent({ imageBuffer }, ref) {
  const imageCanvasRef = useRef<HTMLCanvasElement>(null);
  const frameCanvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const editor = useOverlayEditor(imageCanvasRef, frameCanvasRef, containerRef, imageBuffer);

  return (
    <div
      ref={containerRef}
      className="w-full h-full relative"
      style={{
        outline: "none",
        overflow: "hidden",
        background: "#f0f0f0",
      }}
    >
      {/* Image layer canvas - displays the image */}
      <canvas
        ref={imageCanvasRef}
        className="w-full h-full absolute inset-0"
        style={{ pointerEvents: "none", zIndex: 1 }}
      />
      {/* Frame layer canvas - displays handles and receives mouse events */}
      <canvas
        ref={frameCanvasRef}
        className="w-full h-full absolute inset-0"
        style={{ zIndex: 2 }}
        onMouseDown={(e) => {
          editor?.onMouseDown(e);
        }}
        onMouseMove={(e) => {
          editor?.onMouseMove(e);
        }}
        onMouseUp={(e) => {
          editor?.onMouseUp(e);
        }}
      />
    </div>
  );
});
