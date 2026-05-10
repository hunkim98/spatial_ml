import { PatternSelectorEditor } from "../editor";
import { RefObject, useCallback, useEffect, useState } from "react";

export function usePatternSelectorEditor(
  containerElementRef: RefObject<HTMLDivElement | null>,
  imageCanvasRef: RefObject<HTMLCanvasElement | null>,
  overlayCanvasRef: RefObject<HTMLCanvasElement | null>,
  imageUrl: string
) {
  const [editor, setEditor] = useState<PatternSelectorEditor | null>(null);

  const initialize = useCallback(
    (
      container: HTMLDivElement,
      imageCanvas: HTMLCanvasElement,
      overlayCanvas: HTMLCanvasElement,
      url: string
    ) => {
      const rect = container.getBoundingClientRect();
      const newEditor = new PatternSelectorEditor(
        imageCanvas,
        overlayCanvas,
        rect.width,
        rect.height
      );
      newEditor.loadImageUrl(url);
      setEditor(newEditor);
    },
    []
  );

  // Resize handling
  useEffect(() => {
    const onResize = () => {
      if (
        !containerElementRef.current ||
        !imageCanvasRef.current ||
        !overlayCanvasRef.current ||
        !editor
      ) {
        return;
      }
      const rect = containerElementRef.current.getBoundingClientRect();
      editor.controllers.canvasSizeController.execute({
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
  }, [editor, containerElementRef, imageCanvasRef, overlayCanvasRef]);

  // Initialize editor when refs are ready
  useEffect(() => {
    if (
      !containerElementRef.current ||
      !imageCanvasRef.current ||
      !overlayCanvasRef.current ||
      !imageUrl
    ) {
      return;
    }

    initialize(
      containerElementRef.current,
      imageCanvasRef.current,
      overlayCanvasRef.current,
      imageUrl
    );
  }, [
    initialize,
    containerElementRef,
    imageCanvasRef,
    overlayCanvasRef,
    imageUrl,
  ]);

  return editor;
}
