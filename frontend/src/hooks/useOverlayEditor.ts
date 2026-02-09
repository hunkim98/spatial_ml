import { Editor } from "@/canvas/overlay/editor";
import { RefObject, useCallback, useEffect, useState } from "react";

export function useOverlayEditor(
  imageCanvasRef: RefObject<HTMLCanvasElement | null>,
  frameCanvasRef: RefObject<HTMLCanvasElement | null>,
  containerRef: RefObject<HTMLDivElement | null>,
  imageBuffer: HTMLCanvasElement | null
) {
  const [editor, setEditor] = useState<Editor | null>(null);

  const initialize = useCallback(
    async (
      imageCanvas: HTMLCanvasElement,
      frameCanvas: HTMLCanvasElement,
      container: HTMLDivElement,
      buffer: HTMLCanvasElement
    ) => {
      // Get container dimensions
      const rect = container.getBoundingClientRect();
      const canvasWidth = rect.width > 0 ? rect.width : 800;
      const canvasHeight = rect.height > 0 ? rect.height : 600;

      // Set canvas dimensions
      imageCanvas.width = canvasWidth;
      imageCanvas.height = canvasHeight;
      frameCanvas.width = canvasWidth;
      frameCanvas.height = canvasHeight;

      // Create editor and update with buffer
      const newEditor = new Editor(
        imageCanvas,
        frameCanvas,
        canvasWidth,
        canvasHeight
      );
      newEditor.updateBuffer(buffer);

      setEditor(newEditor);
    },
    []
  );

  useEffect(() => {
    if (!imageCanvasRef.current || !frameCanvasRef.current || !containerRef.current || !imageBuffer) {
      return;
    }

    initialize(imageCanvasRef.current, frameCanvasRef.current, containerRef.current, imageBuffer);
  }, [initialize, imageCanvasRef, frameCanvasRef, containerRef, imageBuffer]);

  return editor;
}
