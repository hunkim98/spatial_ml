import { ClipperEditor } from "@/canvas/clipper/editor";
import { GeoCorners } from "@/canvas/overlay/types";
import { useClipperEditor } from "@/hooks/useClipperEditor";
import { forwardRef, useRef } from "react";

export interface ClipperEditorComponentHandle {
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
  return (
    <div
      className={`w-full h-full relative`}
      ref={containerRef}
      tabIndex={1}
      style={{
        outline: "none",
        // IMPORTANT: DO NOT REMOVE THIS `Background` STYLE
        // This background color is used mask the image when the user is cropping it
        background: "#000000",
      }}
      onMouseDown={() => {
        containerRef.current?.focus();
      }}
      onScroll={(e) => {
        e.stopPropagation();
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
        onWheel={(e) => {
          e.preventDefault();
          editor?.onWheel(e);
        }}
        onMouseDown={(e) => {
          editor?.onMouseDown(e);
        }}
        onMouseMove={(e) => {
          editor?.onMouseMove(e);
        }}
        onMouseUp={() => {
          editor?.onMouseUp();
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
