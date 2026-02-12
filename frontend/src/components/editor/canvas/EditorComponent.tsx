import React, { useEffect } from "react";
import { NoEditorComponent } from "./NoEditorComponent";
import {
  ClipperEditorComponent,
  ClipperEditorComponentHandle,
} from "./ClipperEditorComponent";
import {
  OverlayEditorComponent,
  OverlayEditorComponentHandle,
} from "./OverlayEditorComponent";
import { Loader } from "@mantine/core";
import { MapEditorComponentHandle } from "./MapEditorComponent";
import { GeoCorners } from "@/canvas/overlay/types";

interface EditorComponentProps {
  isLoadingResources: boolean;
  pdfUrl: string | null;
  pageNumber: number;
  clippedImageBuffer: HTMLCanvasElement | null;
  setClippedImageBuffer: React.Dispatch<
    React.SetStateAction<HTMLCanvasElement | null>
  >;
  clipperRef: React.RefObject<ClipperEditorComponentHandle | null>;
  overlayRef: React.RefObject<OverlayEditorComponentHandle | null>;
  mapRef: React.RefObject<MapEditorComponentHandle | null>;
  imageGeoCorners: GeoCorners | null;
  onImageGeoCornersChange?: (corners: GeoCorners) => void;
}

export default function EditorComponent({
  isLoadingResources,
  pdfUrl,
  pageNumber,
  clippedImageBuffer,
  setClippedImageBuffer,
  clipperRef,
  overlayRef,
  mapRef,
  imageGeoCorners,
  onImageGeoCornersChange,
}: EditorComponentProps) {
  // TEMPORARY: Load test image directly for overlay editor testing
  useEffect(() => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.drawImage(img, 0, 0);
        setClippedImageBuffer(canvas);
      }
    };
    img.src = "/anniston-test.png";
  }, []);

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
  return (
    <OverlayEditorComponent
      ref={overlayRef}
      imageBuffer={clippedImageBuffer}
      mapRef={mapRef}
      imageGeoCorners={imageGeoCorners}
      onImageGeoCornersChange={onImageGeoCornersChange}
    />
  );
}
