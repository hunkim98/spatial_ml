"use client";

import {
  useRef,
  useCallback,
  forwardRef,
  useImperativeHandle,
  useEffect,
  useState,
} from "react";
import { Corner } from "@/types/db";
import { MapManager } from "@/map";
import { Editor } from "@/canvas/editor";
import { MapMediaType, EditorMode, GeoCorners, HandleType } from "@/canvas/types";
import { CanvasEvent } from "@/canvas/events";
import { useEditorContext } from "@/canvas/context";
import { OpacitySlider } from "./OpacitySlider";

export interface GeoReferencerHandle {
  flyTo: (center: Corner, zoom?: number) => void;
  fitBounds: (bounds: [number, number, number, number]) => void;
  getCorners: () => GeoCorners | null;
}

interface GeoReferencerProps {
  pdfUrl: string | null;
  pageNumber?: number;
  initialCenter?: Corner;
}

export const GeoReferencer = forwardRef<GeoReferencerHandle, GeoReferencerProps>(
  function GeoReferencer(
    {
      pdfUrl,
      pageNumber = 1,
      initialCenter = { lng: -96.0, lat: 37.0 },
    },
    ref
  ) {
    // ========== Context ==========
    const { opacity } = useEditorContext();

    // ========== Refs ==========
    const containerRef = useRef<HTMLDivElement>(null);
    const mapContainerRef = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const mapManagerRef = useRef<MapManager | null>(null);
    const editorRef = useRef<Editor | null>(null);
    const initialCenterRef = useRef(initialCenter);

    // ========== State ==========
    const [isMapReady, setIsMapReady] = useState(false);
    const [isEditorReady, setIsEditorReady] = useState(false);
    const [editorMode, setEditorMode] = useState<EditorMode>(EditorMode.CREATE);
    const [isInteracting, setIsInteracting] = useState(false);
    const [isOverOverlay, setIsOverOverlay] = useState(false);
    const [cursor, setCursor] = useState<string>("default");

    // ========== Geo/Screen Sync ==========

    const syncGeoCorners = useCallback(() => {
      const editor = editorRef.current;
      const mapManager = mapManagerRef.current;
      if (!editor || !mapManager || !editor.corners) return;

      const geoCorners = mapManager.projection.unprojectCorners(editor.corners);
      editor.setGeoCorners(geoCorners);
    }, []);

    const syncScreenCorners = useCallback(() => {
      const editor = editorRef.current;
      const mapManager = mapManagerRef.current;
      if (!editor || !mapManager || !editor.geoCorners) return;

      const screenCorners = mapManager.projection.projectCorners(editor.geoCorners);
      editor.setCorners(screenCorners);
    }, []);

    // ========== MapLibre Image Management ==========

    const showImageOnMapLibre = useCallback(() => {
      const editor = editorRef.current;
      const mapManager = mapManagerRef.current;
      if (!editor || !mapManager) return;

      const imageUrl = editor.getImageDataUrl();
      const geoCorners = editor.geoCorners;

      if (imageUrl && geoCorners) {
        if (mapManager.imageSource.exists()) {
          mapManager.imageSource.update(geoCorners);
        } else {
          mapManager.imageSource.add(imageUrl, geoCorners, opacity);
        }
      }
    }, [opacity]);

    const hideImageOnMapLibre = useCallback(() => {
      mapManagerRef.current?.imageSource.remove();
    }, []);

    // ========== Interaction State Management ==========

    const startInteraction = useCallback(() => {
      setIsInteracting(true);
      mapManagerRef.current?.lockInteractions();
      hideImageOnMapLibre();

      // Render canvas
      editorRef.current?.render();
    }, [hideImageOnMapLibre]);

    const endInteraction = useCallback(() => {
      setIsInteracting(false);
      setIsOverOverlay(false); // Reset so map can receive events immediately
      syncGeoCorners();

      // Transfer to MapLibre first (before clearing canvas to prevent blink)
      showImageOnMapLibre();

      // Then clear canvas
      editorRef.current?.clearCanvas();

      // Unlock map
      mapManagerRef.current?.unlockInteractions();
    }, [syncGeoCorners, showImageOnMapLibre]);

    // ========== Editor Event Handlers ==========

    const handleBoundsCreated = useCallback(() => {
      syncGeoCorners();
      if (editorRef.current) {
        setEditorMode(editorRef.current.mode);
      }
    }, [syncGeoCorners]);

    const handleTransformChanged = useCallback(() => {
      syncGeoCorners();
    }, [syncGeoCorners]);

    const handleModeChanged = useCallback(() => {
      if (editorRef.current) {
        setEditorMode(editorRef.current.mode);
      }
    }, []);

    // ========== Mouse Handlers ==========

    const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
      const editor = editorRef.current;
      if (!editor) return;

      const consumed = editor.onMouseDown(e);
      if (consumed) {
        e.stopPropagation();
        startInteraction();
      }
    }, [startInteraction]);

    const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
      const editor = editorRef.current;
      if (!editor) return;

      editor.onMouseMove(e);

      const cursorStyle = editor.getCursor(e);
      setCursor(cursorStyle);

      // Track if mouse is over the overlay (for pointer events)
      const isOver = cursorStyle !== "default";
      setIsOverOverlay(isOver);
    }, []);

    const handleMouseUp = useCallback(() => {
      const editor = editorRef.current;
      if (!editor) return;

      const wasInteracting = isInteracting;
      editor.onMouseUp();

      // Only end interaction if we were actually interacting
      if (wasInteracting && editor.isInitialized) {
        endInteraction();
      }
    }, [isInteracting, endInteraction]);

    const handleWheel = useCallback((e: React.WheelEvent<HTMLCanvasElement>) => {
      // Allow wheel zoom when not interacting
      if (isInteracting) return;

      const map = mapManagerRef.current?.getMap();
      if (!map) return;

      const zoom = map.getZoom();
      const zoomDelta = -e.deltaY * 0.01;
      const newZoom = Math.max(0, Math.min(22, zoom + zoomDelta));

      map.easeTo({ zoom: newZoom, duration: 100 });
    }, [isInteracting]);

    // ========== Resize Handler ==========

    const handleResize = useCallback((width: number, height: number) => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      canvas.width = width;
      canvas.height = height;

      // Re-sync screen corners from geo corners after resize
      syncScreenCorners();

      if (isInteracting && editorRef.current?.isLoaded) {
        editorRef.current.render();
      }
    }, [isInteracting, syncScreenCorners]);

    // ========== Imperative Handle Methods ==========

    const flyTo = useCallback((center: Corner, zoom = 12) => {
      mapManagerRef.current?.navigation.flyTo(center, zoom);
    }, []);

    const fitBounds = useCallback((bounds: [number, number, number, number]) => {
      mapManagerRef.current?.navigation.fitBounds(bounds);
    }, []);

    const getCorners = useCallback((): GeoCorners | null => {
      return editorRef.current?.geoCorners ?? null;
    }, []);

    // ========== Effects ==========

    // Initialize MapManager (runs once on mount)
    useEffect(() => {
      if (!mapContainerRef.current) return;

      const mapManager = new MapManager();
      mapManagerRef.current = mapManager;

      mapManager.initialize(mapContainerRef.current, {
        center: initialCenterRef.current,
        zoom: 4,
      }).then(() => {
        setIsMapReady(true);
      });

      return () => {
        mapManager.destroy();
        mapManagerRef.current = null;
      };
    }, []);

    // Initialize Editor when PDF changes
    useEffect(() => {
      if (!pdfUrl) {
        editorRef.current = null;
        setIsEditorReady(false);
        setEditorMode(EditorMode.CREATE);
        setIsInteracting(false);
        return;
      }

      const rafId = requestAnimationFrame(() => {
        const canvas = canvasRef.current;
        const container = containerRef.current;
        if (!canvas || !container) return;

        const rect = container.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          canvas.width = rect.width;
          canvas.height = rect.height;
        }

        const editor = new Editor(MapMediaType.PDF, pdfUrl, canvas, pageNumber);
        editorRef.current = editor;

        editor.load().then(() => {
          setIsEditorReady(true);
          setEditorMode(editor.mode);
        });
      });

      return () => {
        cancelAnimationFrame(rafId);
        editorRef.current = null;
        setIsEditorReady(false);
        setIsInteracting(false);

        const mapManager = mapManagerRef.current;
        if (mapManager) {
          mapManager.unlockInteractions();
          mapManager.imageSource.remove();
        }
      };
    }, [pdfUrl, pageNumber]);

    // Subscribe to editor events
    useEffect(() => {
      const editor = editorRef.current;
      if (!editor || !isEditorReady) return;

      editor.addEventListener(CanvasEvent.BOUNDS_CREATED, handleBoundsCreated);
      editor.addEventListener(CanvasEvent.TRANSFORM_CHANGED, handleTransformChanged);
      editor.addEventListener(CanvasEvent.MODE_CHANGED, handleModeChanged);

      return () => {
        editor.removeEventListener(CanvasEvent.BOUNDS_CREATED, handleBoundsCreated);
        editor.removeEventListener(CanvasEvent.TRANSFORM_CHANGED, handleTransformChanged);
        editor.removeEventListener(CanvasEvent.MODE_CHANGED, handleModeChanged);
      };
    }, [isEditorReady, handleBoundsCreated, handleTransformChanged, handleModeChanged]);

    // Sync screen corners when map moves (when not interacting)
    useEffect(() => {
      const mapManager = mapManagerRef.current;
      if (!mapManager || !isMapReady) return;

      const handleMapMove = () => {
        if (!isInteracting && editorRef.current?.isInitialized) {
          syncScreenCorners();
        }
      };

      mapManager.onMove(handleMapMove);
      return () => mapManager.offMove(handleMapMove);
    }, [isMapReady, isInteracting, syncScreenCorners]);

    // Update MapLibre opacity when it changes
    useEffect(() => {
      const mapManager = mapManagerRef.current;
      if (!mapManager || !mapManager.imageSource.exists()) return;

      mapManager.imageSource.setOpacity(opacity);
    }, [opacity]);

    // Handle container resize
    useEffect(() => {
      const container = containerRef.current;
      if (!container) return;

      const resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const { width, height } = entry.contentRect;
          handleResize(width, height);
        }
      });

      resizeObserver.observe(container);
      return () => resizeObserver.disconnect();
    }, [handleResize]);

    // Track mouse position for overlay detection (document-level to work even with pointer-events: none)
    useEffect(() => {
      const editor = editorRef.current;
      const container = containerRef.current;

      // Only track when editor is initialized and not in CREATE mode
      if (!editor || !editor.isInitialized || editorMode === EditorMode.CREATE) {
        return;
      }

      // Don't track during active interaction
      if (isInteracting) {
        return;
      }

      const handleDocumentMouseMove = (e: MouseEvent) => {
        if (!container) return;

        const rect = container.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Check if inside container bounds
        if (x < 0 || y < 0 || x > rect.width || y > rect.height) {
          setIsOverOverlay(false);
          return;
        }

        // Use editor's hit test to check if over overlay
        const hit = editor.hitTest({ x, y });
        setIsOverOverlay(hit !== HandleType.NONE);
      };

      document.addEventListener("mousemove", handleDocumentMouseMove);
      return () => document.removeEventListener("mousemove", handleDocumentMouseMove);
    }, [editorMode, isInteracting, isEditorReady]);

    // Expose methods to parent
    useImperativeHandle(ref, () => ({
      flyTo,
      fitBounds,
      getCorners,
    }), [flyTo, fitBounds, getCorners]);

    // ========== Render ==========

    const isInitialized = editorRef.current?.isInitialized ?? false;

    // Pointer events logic:
    // - CREATE mode: always capture (need to draw bounds)
    // - Interacting: always capture (dragging)
    // - Initialized + mouse over overlay: capture (to allow clicking to edit)
    // - Otherwise: none (allow map panning)
    const canvasPointerEvents =
      editorMode === EditorMode.CREATE || isInteracting || isOverOverlay
        ? "auto"
        : "none";

    return (
      <div
        ref={containerRef}
        style={{ position: "relative", width: "100%", height: "100%" }}
      >
        {/* MapLibre container */}
        <div ref={mapContainerRef} style={{ position: "absolute", inset: 0 }} />

        {/* Canvas overlay for Editor */}
        {pdfUrl && (
          <canvas
            ref={canvasRef}
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              pointerEvents: canvasPointerEvents,
              cursor: editorMode === EditorMode.CREATE ? "crosshair" : cursor,
            }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
          />
        )}

        {/* Opacity slider (only when initialized) */}
        {isInitialized && <OpacitySlider />}

        {/* Instructions for CREATE mode */}
        {pdfUrl && isEditorReady && editorMode === EditorMode.CREATE && (
          <div style={instructionStyle}>
            Click and drag to draw the PDF overlay bounds
          </div>
        )}

        {/* Instructions for EDIT mode (when interacting) */}
        {pdfUrl && isEditorReady && editorMode === EditorMode.EDIT && isInteracting && (
          <div style={instructionStyle}>
            Drag to move | Drag corners to resize
          </div>
        )}

        {/* Instructions when not interacting */}
        {pdfUrl && isInitialized && !isInteracting && (
          <div style={instructionStyle}>
            Click on overlay to edit | Scroll to zoom
          </div>
        )}
      </div>
    );
  }
);

const instructionStyle: React.CSSProperties = {
  position: "absolute",
  bottom: 20,
  left: "50%",
  transform: "translateX(-50%)",
  background: "rgba(0,0,0,0.7)",
  color: "white",
  padding: "8px 16px",
  borderRadius: 8,
  fontSize: 14,
  zIndex: 20,
  pointerEvents: "none",
};
