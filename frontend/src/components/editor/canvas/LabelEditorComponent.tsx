import React from "react";
import { NoEditorComponent } from "./NoEditorComponent";
import {
  PDFClipperEditorComponent,
  PDFClipperEditorComponentHandle,
} from "./PDFClipperEditorComponent";
import {
  OverlayEditorComponent,
  OverlayEditorComponentHandle,
} from "./OverlayEditorComponent";
import { Loader } from "@mantine/core";
import { MapEditorComponentHandle } from "./MapEditorComponent";
import { GeoCorners } from "@/canvas/overlay/types";
import { ExportResult } from "@/canvas/clipper/controller/exportController";

interface EditorComponentProps {
  isLoadingResources: boolean;
  pdfUrl: string | null;
  pageNumber: number;
  clipResult: ExportResult | null;
  clipperRef: React.RefObject<PDFClipperEditorComponentHandle | null>;
  overlayRef: React.RefObject<OverlayEditorComponentHandle | null>;
  mapRef: React.RefObject<MapEditorComponentHandle | null>;
  imageGeoCorners: GeoCorners | null;
  onImageGeoCornersChange?: (corners: GeoCorners) => void;
  initialBounds?: [[number, number], [number, number]];
  initialImage?: { url: string; corners: GeoCorners; opacity?: number };
  initialClipRect?: { x: number; y: number; width: number; height: number };
}

export default function LabelEditorComponent({
  isLoadingResources,
  pdfUrl,
  pageNumber,
  clipResult,
  clipperRef,
  overlayRef,
  mapRef,
  imageGeoCorners,
  onImageGeoCornersChange,
  initialBounds,
  initialImage,
  initialClipRect,
}: EditorComponentProps) {
  if (isLoadingResources) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <Loader size="xl" />
      </div>
    );
  }

  if (!pdfUrl) {
    return <NoEditorComponent />;
  }

  // Clipping phase
  if (!clipResult) {
    return (
      <PDFClipperEditorComponent
        ref={clipperRef}
        pdfUrl={pdfUrl}
        pageNumber={pageNumber}
        initialClipRect={initialClipRect}
      />
    );
  }

  // Overlay phase
  return (
    <OverlayEditorComponent
      ref={overlayRef}
      imageBuffer={clipResult.buffer}
      mapRef={mapRef}
      imageGeoCorners={imageGeoCorners}
      onImageGeoCornersChange={onImageGeoCornersChange}
      initialBounds={initialBounds}
      initialImage={initialImage}
    />
  );
}
