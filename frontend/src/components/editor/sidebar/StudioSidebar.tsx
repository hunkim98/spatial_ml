import { ImageClipperEditorComponentHandle } from "../canvas/ImageClipperEditorComponent";
import { OverlayEditorComponentHandle } from "../canvas/OverlayEditorComponent";
import { UploadEditorComponentHandle } from "../canvas/UploadEditorComponent";
import { PatternSelectorEditorComponentHandle } from "../canvas/PatternSelectorEditorComponent";
import { MapEditorComponentHandle } from "../canvas/MapEditorComponent";
import { GeoCorners } from "@/canvas/overlay/types";
import { ExportResult } from "@/canvas/clipper/controller/exportController";
import { PatternCircle } from "@/canvas/pattern_selector/types";
import UploadSidebar from "./UploadSidebar";
import PatternSelectorSidebar from "./PatternSelectorSidebar";
import PDFClipperSidebar from "./PDFClipperSidebar";
import OverlaySidebar from "./OverlaySidebar";
import ResultsSidebar from "./ResultsSidebar";

interface StudioSidebarProps {
  mapImageUrl: string | null;
  mapImageFile: File | null;
  mapImageDimensions: { width: number; height: number } | null;
  patterns: PatternCircle[];
  patternsConfirmed: boolean;
  clipResult: ExportResult | null;
  setClipResult: React.Dispatch<React.SetStateAction<ExportResult | null>>;
  uploadRef: React.RefObject<UploadEditorComponentHandle | null>;
  patternSelectorRef: React.RefObject<PatternSelectorEditorComponentHandle | null>;
  clipperRef: React.RefObject<ImageClipperEditorComponentHandle | null>;
  overlayRef: React.RefObject<OverlayEditorComponentHandle | null>;
  mapRef: React.RefObject<MapEditorComponentHandle | null>;
  imageGeoCorners: GeoCorners | null;
  setImageGeoCorners: React.Dispatch<React.SetStateAction<GeoCorners | null>>;
  segmentationResult: GeoJSON.FeatureCollection | null;
  isSegmenting: boolean;
  onBackToUpload: () => void;
  onConfirmPatterns: () => void;
  onBackToPatterns: () => void;
  onBackToClipper: () => void;
  onGeneratePolygons: () => void;
}

export default function StudioSidebar({
  mapImageUrl,
  mapImageFile,
  mapImageDimensions,
  patterns,
  patternsConfirmed,
  clipResult,
  setClipResult,
  uploadRef,
  patternSelectorRef,
  clipperRef,
  overlayRef,
  mapRef,
  imageGeoCorners,
  setImageGeoCorners,
  segmentationResult,
  isSegmenting,
  onBackToUpload,
  onConfirmPatterns,
  onBackToPatterns,
  onBackToClipper,
  onGeneratePolygons,
}: StudioSidebarProps) {
  // Phase 1: Upload
  if (!mapImageUrl) {
    return (
      <UploadSidebar
        uploadRef={uploadRef}
        mapImageFile={mapImageFile}
        mapImageDimensions={mapImageDimensions}
      />
    );
  }

  // Phase 2: Pattern Selection
  if (!patternsConfirmed) {
    return (
      <PatternSelectorSidebar
        patterns={patterns}
        patternSelectorRef={patternSelectorRef}
        onNext={onConfirmPatterns}
        onBack={onBackToUpload}
      />
    );
  }

  // Phase 3: Clip
  if (!clipResult) {
    return (
      <PDFClipperSidebar
        clipperRef={clipperRef}
        setClipResult={setClipResult}
        onSkip={onBackToPatterns}
        onBack={onBackToPatterns}
      />
    );
  }

  // Phase 5: Results
  if (segmentationResult) {
    return (
      <ResultsSidebar
        result={segmentationResult}
        patterns={patterns}
        mapRef={mapRef}
        onBackToGeoreference={() => {
          // TODO: clear segmentation result and go back
        }}
      />
    );
  }

  // Phase 4: Georeference
  return (
    <OverlaySidebar
      clippedImageBuffer={clipResult.buffer}
      overlayRef={overlayRef}
      mapRef={mapRef}
      imageGeoCorners={imageGeoCorners}
      setImageGeoCorners={setImageGeoCorners}
      onSaveLabel={onGeneratePolygons}
      isSaving={isSegmenting}
      onBackToSelectPdf={onBackToPatterns}
      onBackToClipper={onBackToClipper}
    />
  );
}
