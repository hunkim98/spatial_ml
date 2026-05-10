import { PatternSelectorEvent } from "@/canvas/pattern_selector/events";
import { usePatternSelectorEditor } from "@/canvas/pattern_selector/hooks/usePatternSelectorEditor";
import { PatternCircle } from "@/canvas/pattern_selector/types";
import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
} from "react";

export interface PatternSelectorEditorComponentHandle {
  getPatterns: () => PatternCircle[];
  removePattern: (id: string) => void;
  renamePattern: (id: string, name: string) => void;
  exportPatternCrop: (
    id: string
  ) => { buffer: HTMLCanvasElement; size: number } | null;
}

interface PatternSelectorEditorComponentProps {
  imageUrl: string;
  onPatternsChange?: (patterns: PatternCircle[]) => void;
}

export const PatternSelectorEditorComponent = forwardRef<
  PatternSelectorEditorComponentHandle,
  PatternSelectorEditorComponentProps
>(function PatternSelectorEditorComponent(
  { imageUrl, onPatternsChange },
  ref
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imageCanvasRef = useRef<HTMLCanvasElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);

  const editor = usePatternSelectorEditor(
    containerRef,
    imageCanvasRef,
    overlayCanvasRef,
    imageUrl
  );

  // Notify parent when patterns change
  useEffect(() => {
    if (!editor || !onPatternsChange) return;

    const handleChange = () => {
      onPatternsChange(editor.patternCircles);
    };

    editor.addEventListener(PatternSelectorEvent.PATTERN_ADDED, handleChange);
    editor.addEventListener(
      PatternSelectorEvent.PATTERN_REMOVED,
      handleChange
    );
    return () => {
      editor.removeEventListener(
        PatternSelectorEvent.PATTERN_ADDED,
        handleChange
      );
      editor.removeEventListener(
        PatternSelectorEvent.PATTERN_REMOVED,
        handleChange
      );
    };
  }, [editor, onPatternsChange]);

  useImperativeHandle(
    ref,
    () => ({
      getPatterns: () => editor?.patternCircles ?? [],
      removePattern: (id: string) => editor?.removePattern(id),
      renamePattern: (id: string, name: string) =>
        editor?.renamePattern(id, name),
      exportPatternCrop: (id: string) =>
        editor?.exportPatternCrop(id) ?? null,
    }),
    [editor]
  );

  // Wheel event (needs passive: false)
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      editor?.onWheel(e);
    };

    el.addEventListener("wheel", onWheel, { passive: false, capture: true });
    return () => {
      el.removeEventListener("wheel", onWheel, true);
    };
  }, [editor]);

  // Keyboard events on window (so space works without canvas focus)
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => editor?.onKeyDown(e);
    const onKeyUp = (e: KeyboardEvent) => editor?.onKeyUp(e);

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
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
    >
      <canvas
        className="w-full h-full absolute top-0 left-0"
        ref={imageCanvasRef}
        style={{ touchAction: "none" }}
      />
      <canvas
        className="w-full h-full absolute top-0 left-0"
        ref={overlayCanvasRef}
        style={{ touchAction: "none", cursor: editor?.getCursor() ?? "default" }}
        onMouseDown={(e) => {
          editor?.onMouseDown(e);
          if (editor) e.currentTarget.style.cursor = editor.getCursor();
        }}
        onMouseMove={(e) => {
          editor?.onMouseMove(e);
          if (editor) e.currentTarget.style.cursor = editor.getCursor();
        }}
        onMouseUp={(e) => {
          editor?.onMouseUp(e);
          if (editor) e.currentTarget.style.cursor = editor.getCursor();
        }}
      />
    </div>
  );
});
