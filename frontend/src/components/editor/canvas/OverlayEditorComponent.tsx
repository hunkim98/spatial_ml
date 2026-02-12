import { GeoCorners, ScreenCorners } from "@/canvas/overlay/types";
import { Corner } from "@/types/db";
import {
  forwardRef,
  useCallback,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { CornersChangeHandler } from "../../GeoReferencer";
import { useOverlayEditor } from "@/hooks/useOverlayEditor";
import {
  MapEditorComponent,
  MapEditorComponentHandle,
} from "./MapEditorComponent";
import { CanvasController } from "@/canvas/overlay/controller";

export interface ImageInsertResult {
  imageDataUrl: string;
  geoCorners: GeoCorners;
  screenCorners: ScreenCorners;
}

interface OverlayEditorComponentProps {
  imageBuffer: HTMLCanvasElement;
  mapRef: React.RefObject<MapEditorComponentHandle | null>;
}

export interface OverlayEditorComponentHandle {
  flyTo: (center: Corner, zoom?: number) => void;
  fitBounds: (bounds: [number, number, number, number]) => void;
  getCorners: () => GeoCorners | null;
  addCornersChangeListener: (listener: CornersChangeHandler) => void;
  removeCornersChangeListener: (listener: CornersChangeHandler) => void;
  getControllers: () => CanvasController | undefined;
  // preloadMapImage: () => void;
  // insertImage: () => ImageInsertResult | null;
}

export const OverlayEditorComponent = forwardRef<
  OverlayEditorComponentHandle,
  OverlayEditorComponentProps
>(function OverlayEditorComponent({ imageBuffer, mapRef }, ref) {
  const imageCanvasRef = useRef<HTMLCanvasElement>(null);
  const frameCanvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const editor = useOverlayEditor(
    imageCanvasRef,
    frameCanvasRef,
    mapRef,
    containerRef,
    imageBuffer
  );
  const onMapClick = useCallback((lngLat: Corner) => {}, []);
  const [canvasInteractive, setCanvasInteractive] = useState(false);

  const getCorners = useCallback((): GeoCorners | null => {
    const corners = editor?.getScreenCorners();
    if (!corners) return null;
    return mapRef.current?.unprojectScreenCorners(corners) ?? null;
  }, [editor, mapRef]);

  useImperativeHandle(
    ref,
    () => ({
      flyTo: () => {},
      fitBounds: () => {},
      getCorners,
      addCornersChangeListener: () => {},
      removeCornersChangeListener: () => {},
      getControllers: () => editor?.controllers,
    }),
    [editor, getCorners]
  );

  return (
    <div
      ref={containerRef}
      className="w-full h-full relative"
      style={{
        outline: "none",
        overflow: "hidden",
        background: "#f0f0f0",
      }}
      onMouseDown={(e) => {
        // if (!canvasInteractive) return;
        editor?.onMouseDown(
          e as unknown as React.MouseEvent<HTMLCanvasElement>
        );
        if (editor) {
          e.currentTarget.style.cursor = editor.getCursor(e);
        }
      }}
      onMouseMove={(e) => {
        // if (!canvasInteractive) return;
        editor?.onMouseMove(
          e as unknown as React.MouseEvent<HTMLCanvasElement>
        );
        if (editor) {
          e.currentTarget.style.cursor = editor.getCursor(e);
        }
      }}
      onMouseUp={(e) => {
        // if (!canvasInteractive) return;
        editor?.onMouseUp(e as unknown as React.MouseEvent<HTMLCanvasElement>);
        const screenCorners = editor?.getScreenCorners();
        if (screenCorners) {
          const geoCorners =
            mapRef.current?.unprojectScreenCorners(screenCorners);
          if (geoCorners) {
            editor?.setGeoCorners(geoCorners);
          }
        }
        setCanvasInteractive(false);
        if (editor) {
          e.currentTarget.style.cursor = editor.getCursor(e);
        }
      }}
    >
      {/* Image layer canvas - displays the image (visual only) */}
      <canvas
        ref={imageCanvasRef}
        className="w-full h-full absolute inset-0"
        style={{
          zIndex: 1,
          pointerEvents: "none",
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
      <div
        style={{
          pointerEvents: canvasInteractive ? "none" : "auto",
          width: "100%",
          height: "100%",
        }}
      >
        <MapEditorComponent ref={mapRef} onMapClick={onMapClick} />
      </div>
    </div>
  );
});
