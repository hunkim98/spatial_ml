"use client";

import {
  useRef,
  useCallback,
  forwardRef,
  useImperativeHandle,
  useEffect,
  useState,
} from "react";
import { Loader } from "@mantine/core";
import { Corner } from "@/types/db";
import { MapManager } from "@/map";
import { Editor } from "@/canvas/overlay/editor";
import { EditorMode, GeoCorners } from "@/canvas/overlay/types";
import { CanvasEvent } from "@/canvas/overlay/events";
import { useEditorContext } from "@/canvas/overlay/context";
import { OpacitySlider } from "./OpacitySlider";

export type CornersChangeHandler = (corners: GeoCorners) => void;

export interface GeoReferencerHandle {
  flyTo: (center: Corner, zoom?: number) => void;
  fitBounds: (bounds: [number, number, number, number]) => void;
  getCorners: () => GeoCorners | null;
  addCornersChangeListener: (listener: CornersChangeHandler) => void;
  removeCornersChangeListener: (listener: CornersChangeHandler) => void;
}

interface GeoReferencerProps {
  pdfUrl: string | null;
  pageNumber?: number;
  initialCenter?: Corner;
  initialZoom?: number;
  initialCorners?: GeoCorners;
  readOnly?: boolean;
}

export const GeoReferencer = forwardRef<
  GeoReferencerHandle,
  GeoReferencerProps
>(function GeoReferencer(
  {
    pdfUrl,
    pageNumber = 1,
    initialCenter = { lng: -96.0, lat: 37.0 },
    initialZoom = 4,
    initialCorners,
    readOnly = false,
  },
  ref
) {
  // ========== Context ==========
  const { opacity } = useEditorContext();

  // ========== Refs ==========
  const containerRef = useRef<HTMLDivElement>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const imageCanvasRef = useRef<HTMLCanvasElement>(null);
  const frameCanvasRef = useRef<HTMLCanvasElement>(null);
  const mapManagerRef = useRef<MapManager | null>(null);
  const editorRef = useRef<Editor | null>(null);
  const initialCenterRef = useRef(initialCenter);
  const initialZoomRef = useRef(initialZoom);

  // ========== State ==========
  const [isMapReady, setIsMapReady] = useState(false);
  const [isEditorReady, setIsEditorReady] = useState(false);
  const [editorMode, setEditorMode] = useState<EditorMode>(EditorMode.CREATE);
  const [isInteracting, setIsInteracting] = useState(false);
  const [isOverOverlay, setIsOverOverlay] = useState(false);
  const [cursor, setCursor] = useState<string>("default");
  const [cornersChangeListeners, setCornersChangeListeners] = useState<
    CornersChangeHandler[]
  >([]);

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

    const screenCorners = mapManager.projection.projectCorners(
      editor.geoCorners
    );
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
      const corners = editorRef.current.geoCorners;
      if (corners) {
        cornersChangeListeners.forEach((listener) => listener(corners));
      }
    }
  }, [syncGeoCorners, cornersChangeListeners]);

  const handleTransformChanged = useCallback(() => {
    syncGeoCorners();
    const corners = editorRef.current?.geoCorners;
    if (corners) {
      cornersChangeListeners.forEach((listener) => listener(corners));
    }
  }, [syncGeoCorners, cornersChangeListeners]);

  const handleModeChanged = useCallback(() => {
    if (editorRef.current) {
      setEditorMode(editorRef.current.mode);
    }
  }, []);

  // ========== Mouse Handlers ==========

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const editor = editorRef.current;
      if (!editor) return;

      e.stopPropagation();
      startInteraction();
    },
    [startInteraction]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const editor = editorRef.current;
      if (!editor) return;

      editor.onMouseMove(e);

      const cursorStyle = editor.getCursor(e);
      setCursor(cursorStyle);

      // Track if mouse is over the overlay (for pointer events)
      const isOver = cursorStyle !== "default";
      setIsOverOverlay(isOver);
    },
    []
  );

  const handleMouseUp = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const editor = editorRef.current;
      if (!editor) return;

      const wasInteracting = isInteracting;
      editor.onMouseUp(e);

      // Only end interaction if we were actually interacting
      if (wasInteracting && editor.isInitialized) {
        endInteraction();
      }
    },
    [isInteracting, endInteraction]
  );

  const handleWheel = useCallback(
    (e: React.WheelEvent<HTMLCanvasElement>) => {
      // Allow wheel zoom when not interacting
      if (isInteracting) return;

      const map = mapManagerRef.current?.getMap();
      if (!map) return;

      const zoom = map.getZoom();
      const zoomDelta = -e.deltaY * 0.01;
      const newZoom = Math.max(0, Math.min(22, zoom + zoomDelta));

      map.easeTo({ zoom: newZoom, duration: 100 });
    },
    [isInteracting]
  );

  // ========== Resize Handler ==========

  const handleResize = useCallback(
    (width: number, height: number) => {
      const imageCanvas = imageCanvasRef.current;
      const frameCanvas = frameCanvasRef.current;
      if (!imageCanvas || !frameCanvas) return;

      imageCanvas.width = width;
      imageCanvas.height = height;
      frameCanvas.width = width;
      frameCanvas.height = height;

      // Re-sync screen corners from geo corners after resize
      syncScreenCorners();

      if (isInteracting && editorRef.current?.isLoaded) {
        editorRef.current.render();
      }
    },
    [isInteracting, syncScreenCorners]
  );

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

  const addCornersChangeListener = useCallback(
    (listener: CornersChangeHandler) => {
      setCornersChangeListeners((listeners) => [...listeners, listener]);
    },
    []
  );

  const removeCornersChangeListener = useCallback(
    (listener: CornersChangeHandler) => {
      setCornersChangeListeners((listeners) =>
        listeners.filter((l) => l !== listener)
      );
    },
    []
  );

  // ========== Effects ==========

  // Initialize MapManager (runs once on mount)
  useEffect(() => {
    if (!mapContainerRef.current) return;

    const mapManager = new MapManager();
    mapManagerRef.current = mapManager;

    mapManager
      .initialize(mapContainerRef.current, {
        center: initialCenterRef.current,
        zoom: initialZoomRef.current,
      })
      .then(() => {
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
      const imageCanvas = imageCanvasRef.current;
      const frameCanvas = frameCanvasRef.current;
      const container = containerRef.current;
      if (!imageCanvas || !frameCanvas || !container) return;

      const rect = container.getBoundingClientRect();
      const canvasWidth = rect.width > 0 ? rect.width : 800;
      const canvasHeight = rect.height > 0 ? rect.height : 600;

      // Set canvas dimensions
      imageCanvas.width = canvasWidth;
      imageCanvas.height = canvasHeight;
      frameCanvas.width = canvasWidth;
      frameCanvas.height = canvasHeight;

      const editor = new Editor(
        imageCanvas,
        frameCanvas,
        canvasWidth,
        canvasHeight
      );
      editorRef.current = editor;

      editor.updatePdf(pdfUrl, pageNumber).then(() => {
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
    editor.addEventListener(
      CanvasEvent.TRANSFORM_CHANGED,
      handleTransformChanged
    );
    editor.addEventListener(CanvasEvent.MODE_CHANGED, handleModeChanged);

    return () => {
      editor.removeEventListener(
        CanvasEvent.BOUNDS_CREATED,
        handleBoundsCreated
      );
      editor.removeEventListener(
        CanvasEvent.TRANSFORM_CHANGED,
        handleTransformChanged
      );
      editor.removeEventListener(CanvasEvent.MODE_CHANGED, handleModeChanged);
    };
  }, [
    isEditorReady,
    handleBoundsCreated,
    handleTransformChanged,
    handleModeChanged,
  ]);

  // Apply initial corners when both map and editor are ready
  useEffect(() => {
    const editor = editorRef.current;
    const mapManager = mapManagerRef.current;
    if (
      !editor ||
      !mapManager ||
      !isMapReady ||
      !isEditorReady ||
      !initialCorners
    )
      return;

    // Project to screen coordinates
    const screenCorners = mapManager.projection.projectCorners(initialCorners);

    // Initialize editor with pre-set corners
    editor.initializeWithCorners(screenCorners, initialCorners);
    setEditorMode(EditorMode.EDIT);

    // Show on map
    showImageOnMapLibre();
  }, [isMapReady, isEditorReady, initialCorners, showImageOnMapLibre]);

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

      // TODO: Implement overlay hit detection without hitTest
      // For now, assume we're over overlay if editor is initialized
      setIsOverOverlay(isInitialized);
    };

    document.addEventListener("mousemove", handleDocumentMouseMove);
    return () =>
      document.removeEventListener("mousemove", handleDocumentMouseMove);
  }, [editorMode, isInteracting, isEditorReady]);

  // Expose methods to parent
  useImperativeHandle(
    ref,
    () => ({
      flyTo,
      fitBounds,
      getCorners,
      addCornersChangeListener,
      removeCornersChangeListener,
    }),
    [
      flyTo,
      fitBounds,
      getCorners,
      addCornersChangeListener,
      removeCornersChangeListener,
    ]
  );

  // ========== Render ==========

  const isInitialized = editorRef.current?.isInitialized ?? false;
  const isPdfLoading = pdfUrl !== null && !isEditorReady;

  // Pointer events logic:
  // - readOnly: never capture (view only)
  // - CREATE mode: always capture (need to draw bounds)
  // - Interacting: always capture (dragging)
  // - Initialized + mouse over overlay: capture (to allow clicking to edit)
  // - Otherwise: none (allow map panning)
  const canvasPointerEvents = readOnly
    ? "none"
    : editorMode === EditorMode.CREATE || isInteracting || isOverOverlay
      ? "auto"
      : "none";

  return (
    <div
      ref={containerRef}
      style={{ position: "relative", width: "100%", height: "100%" }}
    >
      {/* MapLibre container */}
      <div ref={mapContainerRef} style={{ position: "absolute", inset: 0 }} />

      {/* Loading overlay - dims map while PDF is loading */}
      {isPdfLoading && (
        <div style={loadingOverlayStyle}>
          <Loader size="lg" color="white" />
        </div>
      )}

      {/* Canvas overlay for Editor */}
      {pdfUrl && (
        <>
          {/* Image layer canvas - displays the PDF/image */}
          <canvas
            ref={imageCanvasRef}
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              pointerEvents: "none",
              zIndex: 1,
            }}
          />
          {/* Frame layer canvas - displays handles and receives mouse events */}
          <canvas
            ref={frameCanvasRef}
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              pointerEvents: canvasPointerEvents,
              cursor: editorMode === EditorMode.CREATE ? "crosshair" : cursor,
              zIndex: 2,
            }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
          />
        </>
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
      {pdfUrl &&
        isEditorReady &&
        editorMode === EditorMode.EDIT &&
        isInteracting && (
          <div style={instructionStyle}>
            Drag to move | Drag corners to resize
          </div>
        )}

      {/* Instructions when not interacting (hide in readOnly mode) */}
      {pdfUrl && isInitialized && !isInteracting && !readOnly && (
        <div style={instructionStyle}>
          Click on overlay to edit | Scroll to zoom
        </div>
      )}

      {/* Preview notice for readOnly demo */}
      {readOnly && isInitialized && (
        <div style={previewNoticeStyle}>Preview — Tool in development</div>
      )}
    </div>
  );
});

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

const loadingOverlayStyle: React.CSSProperties = {
  position: "absolute",
  inset: 0,
  background: "rgba(0,0,0,0.5)",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  zIndex: 30,
};

const previewNoticeStyle: React.CSSProperties = {
  position: "absolute",
  top: 12,
  left: 12,
  background: "rgba(0,0,0,0.7)",
  color: "#aaa",
  padding: "6px 12px",
  borderRadius: 6,
  fontSize: 12,
  zIndex: 20,
  pointerEvents: "none",
};
