import React from "react";
import { NoEditorComponent } from "./NoEditorComponent";
import { ClipperEditorComponent } from "./ClipperEditorComponent";
import { OverlayEditorComponent } from "./OverlayEditorComponent";
import { Box, Loader } from "@mantine/core";

interface EditorComponentProps {
  isLoadingResources: boolean;
  pdfUrl: string | null;
  pdfMapFrameImageBuffer: Buffer | null;
  pageNumber: number;
}

function EditorComponent({
  isLoadingResources,
  pdfUrl,
  pdfMapFrameImageBuffer,
  pageNumber,
}: EditorComponentProps) {
  if (isLoadingResources) {
    return <Loader size="xl" />;
  }
  if (!pdfUrl) {
    return <NoEditorComponent />;
  }
  if (!pdfMapFrameImageBuffer) {
    return <ClipperEditorComponent pdfUrl={pdfUrl} pageNumber={pageNumber} />;
  }
  return <OverlayEditorComponent pdfUrl={pdfUrl} pageNumber={pageNumber} />;
}

export default EditorComponent;
