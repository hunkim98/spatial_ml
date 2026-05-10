import { ExportResult } from "@/canvas/clipper/controller/exportController";
import { ClipperEvent, ClipperEventHandler } from "@/canvas/clipper/events";
import { useImageClipperEditor } from "@/canvas/clipper/hooks/useImageClipperEditor";
import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useRef,
} from "react";

export interface ImageClipperEditorComponentHandle {
  exportClippedImage: () => ExportResult | null;
  addEventListener: (
    event: ClipperEvent,
    handler: ClipperEventHandler
  ) => void;
  removeEventListener: (
    event: ClipperEvent,
    handler: ClipperEventHandler
  ) => void;
}

interface ImageClipperEditorComponentProps {
  imageUrl: string;
  initialClipRect?: { x: number; y: number; width: number; height: number };
}

export const ImageClipperEditorComponent = forwardRef<
  ImageClipperEditorComponentHandle,
  ImageClipperEditorComponentProps
>(function ImageClipperEditorComponent({ imageUrl, initialClipRect }, ref) {
  const containerRef = useRef<HTMLDivElement>(null);
  const maskCanvasRef = useRef<HTMLCanvasElement>(null);
  const imageCanvasRef = useRef<HTMLCanvasElement>(null);

  const editor = useImageClipperEditor(
    containerRef,
    maskCanvasRef,
    imageCanvasRef,
    imageUrl
  );

  const pendingListeners = useRef<
    Array<{ event: ClipperEvent; handler: ClipperEventHandler }>
  >([]);

  useLayoutEffect(() => {
    if (!editor) return;
    for (const { event, handler } of pendingListeners.current) {
      editor.addEventListener(event, handler);
    }
    pendingListeners.current = [];
  }, [editor]);

  useEffect(() => {
    if (!editor || !initialClipRect) return;

    const handleImageLoaded = () => {
      editor.controllers.clipRectRestoreController.execute({
        clipRect: initialClipRect,
      });
    };

    editor.addEventListener(ClipperEvent.PDF_LOADED, handleImageLoaded);
    return () => {
      editor.removeEventListener(ClipperEvent.PDF_LOADED, handleImageLoaded);
    };
  }, [editor, initialClipRect]);

  useImperativeHandle(
    ref,
    () => ({
      exportClippedImage: () => {
        if (!editor) return null;
        return editor.exportClippedImage();
      },
      addEventListener: (
        event: ClipperEvent,
        handler: ClipperEventHandler
      ) => {
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

    const onTouch = (e: TouchEvent) => {
      if (e.touches.length > 1) e.preventDefault();
    };

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
      className="w-full h-full relative"
      ref={containerRef}
      tabIndex={1}
      style={{
        outline: "none",
        overflow: "hidden",
        overscrollBehavior: "contain",
        touchAction: "none",
        background: "#000000",
      }}
      onMouseDown={() => containerRef.current?.focus()}
      onKeyDown={(e) => editor?.onKeyDown(e.nativeEvent)}
      onKeyUp={(e) => editor?.onKeyUp(e.nativeEvent)}
    >
      <canvas
        className="w-full h-full absolute top-0 left-0"
        ref={imageCanvasRef}
        style={{ touchAction: "none" }}
        onMouseDown={(e) => {
          editor?.onMouseDown(e);
          if (editor) e.currentTarget.style.cursor = editor.getCursor(e);
        }}
        onMouseMove={(e) => {
          editor?.onMouseMove(e);
          if (editor) e.currentTarget.style.cursor = editor.getCursor(e);
        }}
        onMouseUp={(e) => {
          editor?.onMouseUp(e);
          if (editor) e.currentTarget.style.cursor = editor.getCursor(e);
        }}
      />
      <canvas
        className="w-full h-full absolute top-0 left-0"
        ref={maskCanvasRef}
        style={{ touchAction: "none", pointerEvents: "none" }}
      />
    </div>
  );
});
