import { GeoCorners, HandleType, ScreenCorners } from "@/canvas/overlay/types";
import { Corner } from "@/types/db";
import {
  forwardRef,
  useCallback,
  useEffect,
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
import { detectGeoHandle } from "@/canvas/overlay/utils/geo";

interface OverlayEditorComponentProps {
  imageBuffer: HTMLCanvasElement;
  mapRef: React.RefObject<MapEditorComponentHandle | null>;
  imageGeoCorners: GeoCorners | null;
  onImageGeoCornersChange?: (corners: GeoCorners) => void;
}

export interface OverlayEditorComponentHandle {
  flyTo: (center: Corner, zoom?: number) => void;
  fitBounds: (bounds: [number, number, number, number]) => void;
  getCorners: () => GeoCorners | null;
  addCornersChangeListener: (listener: CornersChangeHandler) => void;
  removeCornersChangeListener: (listener: CornersChangeHandler) => void;
  getControllers: () => CanvasController | undefined;
}

export const OverlayEditorComponent = forwardRef<
  OverlayEditorComponentHandle,
  OverlayEditorComponentProps
>(function OverlayEditorComponent(
  { imageBuffer, mapRef, imageGeoCorners, onImageGeoCornersChange },
  ref
) {
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
  const [mapCursor, setMapCursor] = useState<string | undefined>(undefined);

  // ========== Geo hit detection for cursor ==========

  const resolveGeoCursor = useCallback(
    (e: React.MouseEvent<Element>): string | undefined => {
      if (!imageGeoCorners) return undefined;

      const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
      const screenPoint = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      };
      const mapInstance = mapRef.current?.getMapRef();
      if (!mapInstance) return undefined;

      const lngLat = mapInstance.unproject([screenPoint.x, screenPoint.y]);
      const handle = detectGeoHandle(
        { lng: lngLat.lng, lat: lngLat.lat },
        imageGeoCorners
      );

      switch (handle) {
        case HandleType.BODY:
          return "move";
        case HandleType.TOP_LEFT:
        case HandleType.BOTTOM_RIGHT:
          return "nwse-resize";
        case HandleType.TOP_RIGHT:
        case HandleType.BOTTOM_LEFT:
          return "nesw-resize";
        default:
          return undefined;
      }
    },
    [imageGeoCorners, mapRef]
  );

  // ========== Lift / Drop ==========

  const projectGeoCornersToScreen = useCallback((): ScreenCorners | null => {
    if (!imageGeoCorners) return null;
    const mapInstance = mapRef.current?.getMapRef();
    if (!mapInstance) return null;

    const project = (c: { lng: number; lat: number }) => {
      const p = mapInstance.project([c.lng, c.lat]);
      return { x: p.x, y: p.y };
    };

    return {
      corner1: project(imageGeoCorners.corner1),
      corner2: project(imageGeoCorners.corner2),
      corner3: project(imageGeoCorners.corner3),
      corner4: project(imageGeoCorners.corner4),
    };
  }, [imageGeoCorners, mapRef]);

  const liftImageToCanvas = useCallback(
    (e: React.MouseEvent<Element>) => {
      const screenCorners = projectGeoCornersToScreen();
      if (!screenCorners || !editor) return;

      editor.controllers.transformSessionController.execute({
        action: "begin",
        screenCorners,
      });
      mapRef.current?.hideImageLayer();
      setCanvasInteractive(true);
      setMapCursor(undefined);
    },
    [editor, projectGeoCornersToScreen, mapRef]
  );

  const dropImageToMap = useCallback(() => {
    if (!editor) return;

    // Read final corners before ending session
    const finalCorners = editor.corners;
    if (finalCorners) {
      const geoCorners =
        mapRef.current?.unprojectScreenCorners(finalCorners);
      if (geoCorners) {
        mapRef.current?.updateImageLayerCorners(geoCorners);
        onImageGeoCornersChange?.(geoCorners);
      }
    }

    editor.controllers.transformSessionController.execute({ action: "end" });
    mapRef.current?.showImageLayer();
    setCanvasInteractive(false);
  }, [editor, mapRef, onImageGeoCornersChange]);

  // ========== Space key: toggle map panning during transform ==========

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.code !== "Space" || !canvasInteractive) return;
      e.preventDefault();
      setCanvasInteractive(false);
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.code !== "Space") return;
      // Only re-enable canvas if a transform session is active
      if (editor?.isTransformActive) {
        setCanvasInteractive(true);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, [canvasInteractive, editor]);

  // ========== Imperative handle ==========

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

  // ========== Render ==========

  return (
    <div
      ref={containerRef}
      className="w-full h-full relative"
      tabIndex={0}
      style={{
        outline: "none",
        overflow: "hidden",
        background: "#f0f0f0",
      }}
      onMouseDownCapture={(e) => {
        // Capture phase: intercept BEFORE the map sees the event
        if (!canvasInteractive && resolveGeoCursor(e)) {
          e.stopPropagation();
          liftImageToCanvas(e);
          editor?.onMouseDown(
            e as unknown as React.MouseEvent<HTMLCanvasElement>
          );
        }
      }}
      onMouseDown={(e) => {
        // Bubble phase: only runs if capture didn't stop propagation (normal map clicks)
        if (canvasInteractive) {
          editor?.onMouseDown(
            e as unknown as React.MouseEvent<HTMLCanvasElement>
          );
        }
      }}
      onMouseMove={(e) => {
        if (canvasInteractive) {
          editor?.onMouseMove(
            e as unknown as React.MouseEvent<HTMLCanvasElement>
          );
          editor?.render();
        } else {
          setMapCursor(resolveGeoCursor(e));
        }
      }}
      onMouseUp={(e) => {
        if (canvasInteractive) {
          editor?.onMouseUp(
            e as unknown as React.MouseEvent<HTMLCanvasElement>
          );
          dropImageToMap();
        }
      }}
    >
      <canvas
        ref={imageCanvasRef}
        className="w-full h-full absolute inset-0"
        style={{ zIndex: 1, pointerEvents: "none" }}
      />
      <canvas
        ref={frameCanvasRef}
        className="w-full h-full absolute inset-0"
        style={{ zIndex: 2, pointerEvents: "none" }}
      />
      <div
        style={{
          pointerEvents: canvasInteractive ? "none" : "auto",
          width: "100%",
          height: "100%",
        }}
      >
        <MapEditorComponent
          ref={mapRef}
          onMapClick={onMapClick}
          cursor={mapCursor}
        />
      </div>
    </div>
  );
});
