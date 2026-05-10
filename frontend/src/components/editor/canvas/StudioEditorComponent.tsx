import React from "react";
import {
  UploadEditorComponent,
  UploadEditorComponentHandle,
} from "./UploadEditorComponent";
import {
  PatternSelectorEditorComponent,
  PatternSelectorEditorComponentHandle,
} from "./PatternSelectorEditorComponent";
import {
  ImageClipperEditorComponent,
  ImageClipperEditorComponentHandle,
} from "./ImageClipperEditorComponent";
import {
  OverlayEditorComponent,
  OverlayEditorComponentHandle,
} from "./OverlayEditorComponent";
import PolygonEditorComponent from "./PolygonEditorComponent";
import { MapEditorComponentHandle } from "./MapEditorComponent";
import { GeoCorners } from "@/canvas/overlay/types";
import { ExportResult } from "@/canvas/clipper/controller/exportController";
import { PatternCircle } from "@/canvas/pattern_selector/types";

interface StudioEditorComponentProps {
  /** URL of the uploaded map image (object URL after upload) */
  mapImageUrl: string | null;
  /** Whether pattern selection is confirmed */
  patternsConfirmed: boolean;
  clipResult: ExportResult | null;
  uploadRef: React.RefObject<UploadEditorComponentHandle | null>;
  patternSelectorRef: React.RefObject<PatternSelectorEditorComponentHandle | null>;
  clipperRef: React.RefObject<ImageClipperEditorComponentHandle | null>;
  overlayRef: React.RefObject<OverlayEditorComponentHandle | null>;
  mapRef: React.RefObject<MapEditorComponentHandle | null>;
  imageGeoCorners: GeoCorners | null;
  onImageGeoCornersChange?: (corners: GeoCorners) => void;
  onImageSelect: (
    file: File,
    url: string,
    width: number,
    height: number
  ) => void;
  onPatternsChange: (patterns: PatternCircle[]) => void;
  initialBounds?: [[number, number], [number, number]];
  initialImage?: { url: string; corners: GeoCorners; opacity?: number };
  initialClipRect?: { x: number; y: number; width: number; height: number };
  segmentationResult?: GeoJSON.FeatureCollection | null;
  onGeoJSONChange?: (geojson: GeoJSON.FeatureCollection) => void;
}

export default function StudioEditorComponent({
  mapImageUrl,
  patternsConfirmed,
  clipResult,
  uploadRef,
  patternSelectorRef,
  clipperRef,
  overlayRef,
  mapRef,
  imageGeoCorners,
  onImageGeoCornersChange,
  onImageSelect,
  onPatternsChange,
  initialBounds,
  initialImage,
  initialClipRect,
  segmentationResult,
  onGeoJSONChange,
}: StudioEditorComponentProps) {
  // Phase 1: Upload
  if (!mapImageUrl) {
    return (
      <UploadEditorComponent ref={uploadRef} onImageSelect={onImageSelect} />
    );
  }

  // Phase 2: Pattern Selection
  if (!patternsConfirmed) {
    return (
      <PatternSelectorEditorComponent
        ref={patternSelectorRef}
        imageUrl={mapImageUrl}
        onPatternsChange={onPatternsChange}
      />
    );
  }

  // Phase 3: Clip
  if (!clipResult) {
    return (
      <ImageClipperEditorComponent
        ref={clipperRef}
        imageUrl={mapImageUrl}
        initialClipRect={initialClipRect}
      />
    );
  }

  // Phase 5: Polygon editing (after segmentation)
  if (segmentationResult) {
    return (
      <PolygonEditorComponent
        mapRef={mapRef}
        geojson={segmentationResult}
        onGeoJSONChange={onGeoJSONChange}
        initialBounds={initialBounds}
        initialImage={initialImage}
      />
    );
  }

  // Phase 4: Georeference
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
