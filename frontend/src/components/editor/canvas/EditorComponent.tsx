import React from "react";
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
import { ExportResult } from "@/canvas/clipper/controller/exportController";

interface EditorComponentProps {
  isLoadingResources: boolean;
  pdfUrl: string | null;
  pageNumber: number;
  clipResult: ExportResult | null;
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
  clipResult,
  clipperRef,
  overlayRef,
  mapRef,
  imageGeoCorners,
  onImageGeoCornersChange,
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
      imageBuffer={clipResult.buffer}
      mapRef={mapRef}
      imageGeoCorners={imageGeoCorners}
      onImageGeoCornersChange={onImageGeoCornersChange}
    />
  );
}
