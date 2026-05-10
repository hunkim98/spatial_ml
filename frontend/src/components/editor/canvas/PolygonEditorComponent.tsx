import { GeoCorners } from "@/canvas/overlay/types";
import { useCallback, useEffect, useRef, useState } from "react";
import { useOverlayEditor } from "@/hooks/useOverlayEditor";
import {
  MapEditorComponent,
  MapEditorComponentHandle,
} from "./MapEditorComponent";
import { CanvasEvent } from "@/canvas/overlay/events";
import { Corner } from "@/types/labels";

interface PolygonEditorComponentProps {
  mapRef: React.RefObject<MapEditorComponentHandle | null>;
  geojson: GeoJSON.FeatureCollection;
  onGeoJSONChange?: (geojson: GeoJSON.FeatureCollection) => void;
  initialBounds?: [[number, number], [number, number]];
  initialImage?: { url: string; corners: GeoCorners; opacity?: number };
}

export default function PolygonEditorComponent({
  mapRef,
  geojson,
  onGeoJSONChange,
  initialBounds,
  initialImage,
}: PolygonEditorComponentProps) {
  const imageCanvasRef = useRef<HTMLCanvasElement>(null);
  const frameCanvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Dummy 1×1 canvas — the overlay editor hook requires an imageBuffer
  // but we only use the polygon overlay, not an image layer.
  const [dummyCanvas, setDummyCanvas] = useState<HTMLCanvasElement | null>(null);
  useEffect(() => {
    const c = document.createElement("canvas");
    c.width = 1;
    c.height = 1;
    setDummyCanvas(c);
  }, []);

  const editor = useOverlayEditor(
    imageCanvasRef,
    frameCanvasRef,
    mapRef,
    containerRef,
    dummyCanvas
  );

  const onMapClick = useCallback((_lngLat: Corner) => {}, []);
  const [mapCursor, setMapCursor] = useState<string | undefined>(undefined);

  // ========== Bind projection + load GeoJSON ==========

  useEffect(() => {
    if (!editor || !geojson) return;

    const mapInstance = mapRef.current?.getMapRef();
    if (!mapInstance) return;

    // Bind projection for hit testing + canvas rendering
    editor.setProjection(
      (lngLat) => {
        const p = mapInstance.project([lngLat.lng, lngLat.lat]);
        return { x: p.x, y: p.y };
      },
      (point) => {
        const ll = mapInstance.unproject([point.x, point.y]);
        return { lng: ll.lng, lat: ll.lat };
      }
    );

    // Load GeoJSON into the editor model for hit testing + canvas handles
    editor.setGeoJSON(JSON.parse(JSON.stringify(geojson)));

    // Add GeoJSON to MapLibre so polygons render with colored fills/strokes
    mapRef.current?.addGeoJSONLayer(geojson);

    // Keep projected features current when map moves (pan/zoom)
    const map = mapInstance.getMap();
    const onMapMove = () => {
      editor.controllers.projectionController.execute();
      editor.render();
    };
    map.on("move", onMapMove);

    // On GeoJSON change (after vertex/polygon edit): sync to MapLibre + notify parent
    const onGeoJSONChanged = () => {
      const edited = editor.getGeoJSON();
      if (edited) {
        const clone = JSON.parse(JSON.stringify(edited));
        mapRef.current?.updateGeoJSONLayer(clone);
        onGeoJSONChange?.(clone);
      }
    };
    editor.addEventListener(CanvasEvent.GEOJSON_CHANGED, onGeoJSONChanged);

    return () => {
      map.off("move", onMapMove);
      editor.removeEventListener(
        CanvasEvent.GEOJSON_CHANGED,
        onGeoJSONChanged
      );
    };
    // Only run when editor becomes available — not on every geojson change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editor]);

  // ========== Keyboard events ==========

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.code === "Space") {
        e.preventDefault();
        setMapCursor(undefined);
      }
      editor?.onKeyDown(e);
    };
    const onKeyUp = (e: KeyboardEvent) => {
      editor?.onKeyUp(e);
    };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, [editor]);

  // ========== Render ==========

  if (!dummyCanvas) return null;

  return (
    <div
      ref={containerRef}
      className="w-full h-full relative"
      tabIndex={0}
      style={{
        outline: "none",
        overflow: "hidden",
        background: "#f0f0f0",
        cursor: mapCursor ?? undefined,
      }}
      onMouseDownCapture={(e) => {
        if (editor?.isSpaceHeld) return;

        // Check if hover hit test found a candidate (vertex, edge, or polygon body)
        const cursor = editor?.getCursor();
        if (cursor && cursor !== "default") {
          e.stopPropagation();
          editor?.onMouseDown(
            e as unknown as React.MouseEvent<HTMLCanvasElement>
          );
          editor?.render();
        }
        // If no candidate, don't stop propagation — map pans normally
      }}
      onMouseMove={(e) => {
        if (editor?.isSpaceHeld) {
          setMapCursor(undefined);
          return;
        }

        if (editor?.isPolygonDragging) {
          // Active drag: update vertex/polygon position + render canvas
          editor.onMouseMove(
            e as unknown as React.MouseEvent<HTMLCanvasElement>
          );
          editor.render();
          // Sync the editing polygon to MapLibre in real-time
          const edited = editor.getGeoJSON();
          if (edited) {
            mapRef.current?.updateGeoJSONLayer(
              JSON.parse(JSON.stringify(edited))
            );
          }
        } else {
          // Hover: project features, run hit test, update cursor + render handles
          editor?.controllers.projectionController.execute();
          editor?.onMouseMove(
            e as unknown as React.MouseEvent<HTMLCanvasElement>
          );
          setMapCursor(editor?.getCursor());
          editor?.render();
        }
      }}
      onMouseUp={(e) => {
        if (editor?.isPolygonDragging && !editor.isSpaceHeld) {
          editor.onMouseUp(
            e as unknown as React.MouseEvent<HTMLCanvasElement>
          );
          editor.render();
          // GEOJSON_CHANGED event is dispatched by the tool controller on mouseup,
          // which triggers the event listener to sync to MapLibre + notify parent
        }
      }}
      onWheel={(e) => {
        // No special wheel handling — map handles zoom directly
        // (map div always has pointer-events: auto)
        // Just re-render canvas handles after zoom settles
        requestAnimationFrame(() => editor?.render());
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
      <div style={{ width: "100%", height: "100%" }}>
        <MapEditorComponent
          ref={mapRef}
          onMapClick={onMapClick}
          cursor={mapCursor}
          initialBounds={initialBounds}
          initialImage={initialImage}
        />
      </div>
    </div>
  );
}
