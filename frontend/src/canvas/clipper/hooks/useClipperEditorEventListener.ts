import { useEffect } from "react";
import { ClipperEditor } from "../editor";
import { ClipperEvent, ClipperEventHandler } from "../events";

/**
 * Subscribe to a ClipperEditor event. Automatically cleans up on unmount
 * or when the editor/event/handler changes.
 */
export function useClipperEditorEventListener(
  editor: ClipperEditor | null,
  event: ClipperEvent,
  handler: ClipperEventHandler
) {
  useEffect(() => {
    if (!editor) return;
    editor.addEventListener(event, handler);
    return () => {
      editor.removeEventListener(event, handler);
    };
  }, [editor, event, handler]);
}
