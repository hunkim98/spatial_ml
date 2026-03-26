import { ClipperEditorComponentHandle } from "../canvas/ClipperEditorComponent";
import { OverlayEditorComponentHandle } from "../canvas/OverlayEditorComponent";
import { MapEditorComponentHandle } from "../canvas/MapEditorComponent";
import { GeoCorners } from "@/canvas/overlay/types";
import { PdfFile } from "@/types/pdf";
import { GeoLabel, SkippedLabel } from "@/types/labels";
import { ExportResult } from "@/canvas/clipper/controller/exportController";
import LoadingSidebar from "./LoadingSidebar";
import PdfSelectSidebar from "./PdfSelectSidebar";
import ClipperSidebar from "./ClipperSidebar";
import OverlaySidebar from "./OverlaySidebar";

interface EditorSidebarProps {
  pdfs: PdfFile[];
  labels: Record<string, GeoLabel>;
  skippedLabels: Record<string, SkippedLabel>;
  selectedPdf: PdfFile | null;
  onPdfSelect: (hash: string | null) => void;
  isLoadingResources: boolean;
  pdfUrl: string | null;
  clipResult: ExportResult | null;
  setClipResult: React.Dispatch<React.SetStateAction<ExportResult | null>>;
  clipperRef: React.RefObject<ClipperEditorComponentHandle | null>;
  overlayRef: React.RefObject<OverlayEditorComponentHandle | null>;
  mapRef: React.RefObject<MapEditorComponentHandle | null>;
  imageGeoCorners: GeoCorners | null;
  setImageGeoCorners: React.Dispatch<React.SetStateAction<GeoCorners | null>>;
  onSkip: () => void;
  onSaveLabel: () => void;
  isSaving: boolean;
  onBack: () => void;
  onBackToClipper: () => void;
}

export default function EditorSidebar({
  pdfs,
  labels,
  skippedLabels,
  selectedPdf,
  onPdfSelect,
  clipResult,
  setClipResult,
  isLoadingResources,
  pdfUrl,
  clipperRef,
  overlayRef,
  mapRef,
  imageGeoCorners,
  setImageGeoCorners,
  onSkip,
  onSaveLabel,
  isSaving,
  onBack,
  onBackToClipper,
}: EditorSidebarProps) {
  if (isLoadingResources) {
    return <LoadingSidebar />;
  }

  if (!pdfUrl) {
    return (
      <PdfSelectSidebar
        pdfs={pdfs}
        labels={labels}
        skippedLabels={skippedLabels}
        onPdfSelect={onPdfSelect}
      />
    );
  }
  if (!clipResult) {
    return (
      <ClipperSidebar
        selectedPdf={selectedPdf}
        clipperRef={clipperRef}
        setClipResult={setClipResult}
        onSkip={onSkip}
        onBack={onBack}
      />
    );
  }
  return (
    <OverlaySidebar
      selectedPdf={selectedPdf}
      clippedImageBuffer={clipResult.buffer}
      overlayRef={overlayRef}
      mapRef={mapRef}
      imageGeoCorners={imageGeoCorners}
      setImageGeoCorners={setImageGeoCorners}
      onSaveLabel={onSaveLabel}
      isSaving={isSaving}
      onBackToSelectPdf={onBack}
      onBackToClipper={onBackToClipper}
    />
  );
}
