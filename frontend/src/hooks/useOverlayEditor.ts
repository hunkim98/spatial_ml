import { Editor } from "@/canvas/overlay/editor";
import { MapMediaType } from "@/canvas/overlay/types";
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

      // Create editor with image type
      const newEditor = new Editor(
        MapMediaType.IMAGE,
        "", // empty URL since we load from buffer
        imageCanvas,
        frameCanvas,
        canvasWidth,
        canvasHeight,
        1
      );

      // Use ImageUploadController to load the buffer (following MVC pattern)
      newEditor.controllers.imageUploadController.execute({ buffer });

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
