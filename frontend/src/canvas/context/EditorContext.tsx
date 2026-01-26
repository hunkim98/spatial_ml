"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

interface EditorContextValue {
  opacity: number;
  setOpacity: (opacity: number) => void;
}

const EditorContext = createContext<EditorContextValue | null>(null);

export function EditorProvider({ children }: { children: ReactNode }) {
  const [opacity, setOpacityState] = useState(0.7);

  const setOpacity = useCallback((value: number) => {
    setOpacityState(Math.max(0.1, Math.min(1, value)));
  }, []);

  return (
    <EditorContext.Provider value={{ opacity, setOpacity }}>
      {children}
    </EditorContext.Provider>
  );
}

export function useEditorContext() {
  const context = useContext(EditorContext);
  if (!context) {
    throw new Error("useEditorContext must be used within EditorProvider");
  }
  return context;
}
