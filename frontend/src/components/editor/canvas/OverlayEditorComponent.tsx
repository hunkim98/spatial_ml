import { GeoCorners, HandleType, ScreenCorners } from "@/canvas/overlay/types";
import { Corner } from "@/types/labels";
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { Slider, Text, Group, Paper } from "@mantine/core";
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
  initialBounds?: [[number, number], [number, number]];
  initialImage?: { url: string; corners: GeoCorners; opacity?: number };
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
  { imageBuffer, mapRef, imageGeoCorners, onImageGeoCornersChange, initialBounds, initialImage },
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
  const [opacity, setOpacity] = useState(0.7);

  const handleOpacityChange = useCallback(
    (value: number) => {
      setOpacity(value);
      mapRef.current?.setImageLayerOpacity(value);
    },
    [mapRef]
  );

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
    mapRef.current?.showImageLayer(opacity);
    setCanvasInteractive(false);
  }, [editor, mapRef, onImageGeoCornersChange, opacity]);

  // ========== Keyboard events: delegate to editor + toggle canvas ==========

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.code === "Space") {
        e.preventDefault();
        setMapCursor(undefined);
        if (canvasInteractive) {
          setCanvasInteractive(false);
        }
      }
      editor?.onKeyDown(e);
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.code === "Space" && editor?.isTransformActive) {
        setCanvasInteractive(true);
      }
      editor?.onKeyUp(e);
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
        // Skip when space is held so the map can be navigated freely
        if (
          !canvasInteractive &&
          !editor?.isSpaceHeld &&
          resolveGeoCursor(e)
        ) {
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
        } else if (!editor?.isSpaceHeld) {
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
          initialBounds={initialBounds}
          initialImage={initialImage}
        />
      </div>

      {/* Floating opacity slider */}
      {imageGeoCorners && (
        <Paper
          shadow="md"
          p="sm"
          radius="md"
          style={{
            position: "absolute",
            bottom: 24,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 30,
            minWidth: 200,
            background: "rgba(255, 255, 255, 0.95)",
            pointerEvents: "auto",
          }}
        >
          <Group gap="xs" mb={4}>
            <Text size="xs" fw={500}>
              Opacity
            </Text>
            <Text size="xs" c="dimmed">
              {Math.round(opacity * 100)}%
            </Text>
          </Group>
          <Slider
            value={opacity}
            onChange={handleOpacityChange}
            min={0}
            max={1}
            step={0.05}
            size="sm"
          />
        </Paper>
      )}
    </div>
  );
});
