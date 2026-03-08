import { ExportResult } from "@/canvas/clipper/controller/exportController";
import { ClipperEvent, ClipperEventHandler } from "@/canvas/clipper/events";
import { useClipperEditor } from "@/canvas/clipper/hooks/useClipperEditor";
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useRef,
} from "react";

export interface ClipperEditorComponentHandle {
  exportClippedImage: () => ExportResult | null;
  addEventListener: (event: ClipperEvent, handler: ClipperEventHandler) => void;
  removeEventListener: (
    event: ClipperEvent,
    handler: ClipperEventHandler
  ) => void;
}

interface ClipperEditorComponentProps {
  pdfUrl: string;
  pageNumber: number;
  initialClipRect?: { x: number; y: number; width: number; height: number };
}

export const ClipperEditorComponent = forwardRef<
  ClipperEditorComponentHandle,
  ClipperEditorComponentProps
>(function PDFMapFrameExtractor({ pdfUrl, pageNumber, initialClipRect }, ref) {
  const containerRef = useRef<HTMLDivElement>(null);
  const maskCanvasRef = useRef<HTMLCanvasElement>(null);
  const pdfCanvasRef = useRef<HTMLCanvasElement>(null);

  const editor = useClipperEditor(
    containerRef,
    maskCanvasRef,
    pdfCanvasRef,
    pdfUrl
  );

  // Buffer listeners added before editor is ready
  const pendingListeners = useRef<
    Array<{ event: ClipperEvent; handler: ClipperEventHandler }>
  >([]);

  // Flush pending listeners synchronously when editor becomes available.
  // useLayoutEffect runs before any async callbacks (like PDF fetch completing),
  // so listeners are guaranteed to be attached before events fire.
  useLayoutEffect(() => {
    if (!editor) return;
    for (const { event, handler } of pendingListeners.current) {
      editor.addEventListener(event, handler);
    }
    pendingListeners.current = [];
  }, [editor]);

  // Restore clip rect after PDF loads (when returning from overlay phase)
  useEffect(() => {
    if (!editor || !initialClipRect) return;

    const handlePdfLoaded = () => {
      editor.controllers.clipRectRestoreController.execute({
        clipRect: initialClipRect,
      });
    };

    editor.addEventListener(ClipperEvent.PDF_LOADED, handlePdfLoaded);
    return () => {
      editor.removeEventListener(ClipperEvent.PDF_LOADED, handlePdfLoaded);
    };
  }, [editor, initialClipRect]);

  // Expose methods via ref
  useImperativeHandle(
    ref,
    () => ({
      exportClippedImage: () => {
        if (!editor) return null;
        return editor.exportClippedImage();
      },
      addEventListener: (event: ClipperEvent, handler: ClipperEventHandler) => {
        if (editor) {
          editor.addEventListener(event, handler);
        } else {
          pendingListeners.current.push({ event, handler });
        }
      },
      removeEventListener: (
        event: ClipperEvent,
        handler: ClipperEventHandler
      ) => {
        if (editor) {
          editor.removeEventListener(event, handler);
        } else {
          pendingListeners.current = pendingListeners.current.filter(
            (l) => !(l.event === event && l.handler === handler)
          );
        }
      },
    }),
    [editor]
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    // Mobile pinch (touch)
    const onTouch = (e: TouchEvent) => {
      if (e.touches.length > 1) e.preventDefault();
    };

    // Wheel: must be non-passive so preventDefault works
    // (React onWheel is passive and cannot preventDefault)
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      editor?.onWheel(e);
    };

    el.addEventListener("touchstart", onTouch, { passive: false });
    el.addEventListener("touchmove", onTouch, { passive: false });
    el.addEventListener("wheel", onWheel, { passive: false, capture: true });

    return () => {
      el.removeEventListener("touchstart", onTouch);
      el.removeEventListener("touchmove", onTouch);
      el.removeEventListener("wheel", onWheel, true);
    };
  }, [editor]);

  return (
    <div
      className={`w-full h-full relative`}
      ref={containerRef}
      tabIndex={1}
      style={{
        outline: "none",
        overflow: "hidden",
        // IMPORTANT: DO NOT REMOVE THIS `Background` STYLE
        // This background color is used mask the image when the user is cropping it
        overscrollBehavior: "contain",
        touchAction: "none",
        background: "#000000",
      }}
      onMouseDown={() => {
        containerRef.current?.focus();
      }}
      onKeyDown={(e) => {
        editor?.onKeyDown(e.nativeEvent);
      }}
      onKeyUp={(e) => {
        editor?.onKeyUp(e.nativeEvent);
      }}
    >
      <canvas
        id="pdf-canvas"
        className="w-full h-full absolute top-0 left-0"
        ref={pdfCanvasRef}
        style={{
          touchAction: "none",
        }}
        onMouseDown={(e) => {
          editor?.onMouseDown(e);
          if (editor) {
            e.currentTarget.style.cursor = editor.getCursor(e);
          }
        }}
        onMouseMove={(e) => {
          editor?.onMouseMove(e);
          if (editor) {
            e.currentTarget.style.cursor = editor.getCursor(e);
          }
        }}
        onMouseUp={(e) => {
          editor?.onMouseUp(e);
          if (editor) {
            e.currentTarget.style.cursor = editor.getCursor(e);
          }
        }}
      />
      <canvas
        id="mask-canvas"
        className="w-full h-full absolute top-0 left-0"
        ref={maskCanvasRef}
        style={{
          touchAction: "none",
          pointerEvents: "none",
        }}
      />
    </div>
  );
});
