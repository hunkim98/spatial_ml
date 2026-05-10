import { ClipperEditor } from "../editor";
import { RefObject, useCallback, useEffect, useState } from "react";

export function useImageClipperEditor(
  containerElementRef: RefObject<HTMLDivElement | null>,
  maskCanvasRef: RefObject<HTMLCanvasElement | null>,
  imageCanvasRef: RefObject<HTMLCanvasElement | null>,
  imageUrl: string
) {
  const [editor, setEditor] = useState<ClipperEditor | null>(null);

  const initialize = useCallback(
    async (
      container: HTMLDivElement,
      imageCanvas: HTMLCanvasElement,
      maskCanvas: HTMLCanvasElement,
      imageUrl: string
    ) => {
      const rect = container.getBoundingClientRect();
      const newEditor = new ClipperEditor(
        imageCanvas,
        maskCanvas,
        rect.width,
        rect.height
      );
      newEditor.updateImage(imageUrl);
      setEditor(newEditor);
    },
    []
  );

  useEffect(() => {
    const onResize = () => {
      if (
        !containerElementRef.current ||
        !imageCanvasRef.current ||
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
  }, [editor, containerElementRef, imageCanvasRef, maskCanvasRef]);

  useEffect(() => {
    if (
      !containerElementRef.current ||
      !maskCanvasRef.current ||
      !imageCanvasRef.current ||
      !imageUrl
    ) {
      return;
    }

    initialize(
      containerElementRef.current,
      imageCanvasRef.current,
      maskCanvasRef.current,
      imageUrl
    );
  }, [initialize, containerElementRef, maskCanvasRef, imageCanvasRef, imageUrl]);

  return editor;
}
