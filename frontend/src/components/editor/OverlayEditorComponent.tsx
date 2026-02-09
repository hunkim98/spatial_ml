import { GeoCorners } from "@/canvas/overlay/types";
import { Corner } from "@/types/db";
import { forwardRef, useCallback, useRef, useState } from "react";
import { CornersChangeHandler } from "../GeoReferencer";
import { useOverlayEditor } from "@/hooks/useOverlayEditor";
import { MapEditorComponent } from "./MapEditorComponent";
import { SegmentedControl, Paper } from "@mantine/core";
import { IconPencil, IconMap } from "@tabler/icons-react";

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
  const [mode, setMode] = useState<"map" | "pencil">("map");

  const editor = useOverlayEditor(
    imageCanvasRef,
    frameCanvasRef,
    containerRef,
    imageBuffer
  );
  const onMapClick = useCallback((lngLat: Corner) => {}, []);

  const [canvasInteractive, setCanvasInteractive] = useState(false);

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
      {/* Mode toggle control */}
      <Paper
        shadow="md"
        style={{
          position: "absolute",
          bottom: 20,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 10,
          padding: 4,
        }}
      >
        <SegmentedControl
          value={mode}
          onChange={(value) => {
            setMode(value as "map" | "pencil");
            setCanvasInteractive(value === "pencil");
          }}
          data={[
            {
              value: "map",
              label: (
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <IconMap size={18} />
                  <span>Map</span>
                </div>
              ),
            },
            {
              value: "pencil",
              label: (
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <IconPencil size={18} />
                  <span>Overlay</span>
                </div>
              ),
            },
          ]}
        />
      </Paper>

      {/* Image layer canvas - displays the image and receives events when active */}
      <canvas
        ref={imageCanvasRef}
        className="w-full h-full absolute inset-0"
        style={{
          pointerEvents: canvasInteractive ? "auto" : "none",
          zIndex: 1,
        }}
        onMouseDown={(e) => {
          if (canvasInteractive && editor) {
            editor.onMouseDown(e);
          }
        }}
        onMouseMove={(e) => {
          if (canvasInteractive && editor) {
            editor.onMouseMove(e);
          }
        }}
        onMouseUp={(e) => {
          if (canvasInteractive && editor) {
            editor.onMouseUp(e);
          }
        }}
      />
      {/* Frame layer canvas - displays handles (visual only) */}
      <canvas
        ref={frameCanvasRef}
        className="w-full h-full absolute inset-0"
        style={{
          zIndex: 2,
          pointerEvents: "none",
        }}
      />
      <MapEditorComponent onMapClick={onMapClick} />
    </div>
  );
});
