import { PdfFile } from "@/types/pdf";
import { ClipperEditorComponentHandle } from "../canvas/ClipperEditorComponent";
import { OverlayEditorComponentHandle } from "../canvas/OverlayEditorComponent";
import { MapEditorComponentHandle } from "../canvas/MapEditorComponent";
import { GeoCorners } from "@/canvas/overlay/types";
import { ExportResult } from "@/canvas/clipper/controller/exportController";
import LoadingSidebar from "./LoadingSidebar";
import PdfSelectSidebar from "./PdfSelectSidebar";
import ClipperSidebar from "./ClipperSidebar";
import OverlaySidebar from "./OverlaySidebar";

interface LabelStudioSidebarProps {
  pdfs: PdfFile[];
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
}

export default function LabelStudioSidebar({
  pdfs,
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
}: LabelStudioSidebarProps) {
  if (isLoadingResources) {
    return <LoadingSidebar />;
  }

  if (!pdfUrl) {
    return <PdfSelectSidebar pdfs={pdfs} onPdfSelect={onPdfSelect} />;
  }
  if (!clipResult) {
    return (
      <ClipperSidebar
        clipperRef={clipperRef}
        setClipResult={setClipResult}
      />
    );
  }
  return (
    <OverlaySidebar
      clippedImageBuffer={clipResult.buffer}
      setClipResult={setClipResult}
      overlayRef={overlayRef}
      mapRef={mapRef}
      imageGeoCorners={imageGeoCorners}
      setImageGeoCorners={setImageGeoCorners}
    />
  );
}
