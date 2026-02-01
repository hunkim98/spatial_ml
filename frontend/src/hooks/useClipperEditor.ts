import { ClipperEditor } from "@/canvas/clipper/editor";
import { RefObject, useCallback, useEffect, useState } from "react";

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
      const rect = container.getBoundingClientRect();
      const newEditor = new ClipperEditor(
        pdfCanvas,
        maskCanvas,
        rect.width,
        rect.height
      );
      newEditor.updatePdf(pdfUrl, 1);

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
      const rect = containerElementRef.current.getBoundingClientRect();
      editor.controllers.canvasSizeScaleController.execute({
        width: rect.width,
        height: rect.height,
      });

      editor.render();
    };
    onResize();

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
