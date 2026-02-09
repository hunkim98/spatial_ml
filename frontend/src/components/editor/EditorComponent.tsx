import React, { forwardRef, useImperativeHandle, useRef, useState } from "react";
import { NoEditorComponent } from "./NoEditorComponent";
import {
  ClipperEditorComponent,
  ClipperEditorComponentHandle,
} from "./ClipperEditorComponent";
import { OverlayEditorComponent } from "./OverlayEditorComponent";
import { Loader } from "@mantine/core";

interface EditorComponentProps {
  isLoadingResources: boolean;
  pdfUrl: string | null;
  pageNumber: number;
}

export interface EditorComponentHandle {
  applyClip: () => boolean;
  resetToClipper: () => void;
  hasClippedImage: () => boolean;
}

const EditorComponent = forwardRef<EditorComponentHandle, EditorComponentProps>(
  function EditorComponent({ isLoadingResources, pdfUrl, pageNumber }, ref) {
    const clipperRef = useRef<ClipperEditorComponentHandle>(null);
    const [clippedImageBuffer, setClippedImageBuffer] =
      useState<HTMLCanvasElement | null>(null);

    useImperativeHandle(ref, () => ({
      applyClip: () => {
        if (!clipperRef.current) return false;
        const result = clipperRef.current.exportClippedImage();
        if (result) {
          setClippedImageBuffer(result.buffer);
          return true;
        }
        return false;
      },
      resetToClipper: () => {
        setClippedImageBuffer(null);
      },
      hasClippedImage: () => {
        return clippedImageBuffer !== null;
      },
    }));

    if (isLoadingResources) {
      return <Loader size="xl" />;
    }

    if (!pdfUrl) {
      return <NoEditorComponent />;
    }

    // Clipping phase
    if (!clippedImageBuffer) {
      return (
        <ClipperEditorComponent
          ref={clipperRef}
          pdfUrl={pdfUrl}
          pageNumber={pageNumber}
        />
      );
    }

    // Overlay phase
    return <OverlayEditorComponent imageBuffer={clippedImageBuffer} />;
  }
);

export default EditorComponent;
