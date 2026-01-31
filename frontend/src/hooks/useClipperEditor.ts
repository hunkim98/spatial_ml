import { ClipperEditor } from "@/canvas/clipper/editor";
import { RefObject, useCallback, useEffect, useState } from "react";

const setCanvasResolution = (
  canvas: HTMLCanvasElement,
  container: HTMLDivElement
) => {
  const rect = container.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;

  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
};

export function useClipperEditor(
  containerElementRef: RefObject<HTMLDivElement | null>,
  maskCanvasRef: RefObject<HTMLCanvasElement | null>,
  pdfCanvasRef: RefObject<HTMLCanvasElement | null>,
  pdfUrl: string
) {
  const [editor, setEditor] = useState<ClipperEditor | null>(null);

  const initialize = useCallback(
    async (
      container: HTMLDivElement,
      pdfCanvas: HTMLCanvasElement,
      maskCanvas: HTMLCanvasElement,
      pdfUrl: string
    ) => {
      // Set canvas resolution before creating editor
      setCanvasResolution(pdfCanvas, container);
      setCanvasResolution(maskCanvas, container);

      const newEditor = new ClipperEditor(pdfUrl, pdfCanvas, maskCanvas, 1);

      // Load the PDF and render
      await newEditor.load();

      setEditor(newEditor);
    },
    []
  );

  useEffect(() => {
    const onResize = () => {
      if (
        !containerElementRef.current ||
        !pdfCanvasRef.current ||
        !maskCanvasRef.current ||
        !editor
      ) {
        return;
      }

      setCanvasResolution(pdfCanvasRef.current, containerElementRef.current);
      setCanvasResolution(maskCanvasRef.current, containerElementRef.current);
      editor.render();
    };

    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
    };
  }, [editor, containerElementRef, pdfCanvasRef, maskCanvasRef]);

  useEffect(() => {
    if (
      !containerElementRef.current ||
      !maskCanvasRef.current ||
      !pdfCanvasRef.current ||
      !pdfUrl
    ) {
      return;
    }

    initialize(
      containerElementRef.current,
      pdfCanvasRef.current,
      maskCanvasRef.current,
      pdfUrl
    );
  }, [initialize, containerElementRef, maskCanvasRef, pdfCanvasRef, pdfUrl]);

  return editor;
}
