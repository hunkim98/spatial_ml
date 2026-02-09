import { ClipperEditor } from "@/canvas/clipper/editor";
import { ExportResult } from "@/canvas/clipper/controller/exportController";
import { GeoCorners } from "@/canvas/overlay/types";
import { useClipperEditor } from "@/hooks/useClipperEditor";
import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

export interface ClipperEditorComponentHandle {
  exportClippedImage: () => ExportResult | null;
  extractFrame: (corners: GeoCorners) => Promise<string>;
  exportImage: (image: string) => Promise<string>;
}

interface ClipperEditorComponentProps {
  pdfUrl: string;
  pageNumber: number;
}

export const ClipperEditorComponent = forwardRef<
  ClipperEditorComponentHandle,
  ClipperEditorComponentProps
>(function PDFMapFrameExtractor({ pdfUrl, pageNumber }, ref) {
  const containerRef = useRef<HTMLDivElement>(null);
  const maskCanvasRef = useRef<HTMLCanvasElement>(null);
  const pdfCanvasRef = useRef<HTMLCanvasElement>(null);

  const editor = useClipperEditor(
    containerRef,
    maskCanvasRef,
    pdfCanvasRef,
    pdfUrl
  );

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    exportClippedImage: () => {
      if (!editor) return null;
      return editor.exportClippedImage();
    },
    extractFrame: async (corners: GeoCorners) => {
      // TODO: implement if needed
      throw new Error("Not implemented");
    },
    exportImage: async (image: string) => {
      // TODO: implement if needed
      throw new Error("Not implemented");
    },
  }));

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
