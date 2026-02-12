import { ClipperEditorComponentHandle } from "../canvas/ClipperEditorComponent";
import { OverlayEditorComponentHandle } from "../canvas/OverlayEditorComponent";
import { MapEditorComponentHandle } from "../canvas/MapEditorComponent";
import { GeoCorners } from "@/canvas/overlay/types";
import LoadingSidebar from "./LoadingSidebar";
import PdfSelectSidebar from "./PdfSelectSidebar";
import ClipperSidebar from "./ClipperSidebar";
import OverlaySidebar from "./OverlaySidebar";

interface EditorSidebarProps {
  isLoadingResources: boolean;
  pdfUrl: string | null;
  clippedImageBuffer: HTMLCanvasElement | null;
  setClippedImageBuffer: React.Dispatch<
    React.SetStateAction<HTMLCanvasElement | null>
  >;
  clipperRef: React.RefObject<ClipperEditorComponentHandle | null>;
  overlayRef: React.RefObject<OverlayEditorComponentHandle | null>;
  mapRef: React.RefObject<MapEditorComponentHandle | null>;
  imageGeoCorners: GeoCorners | null;
  setImageGeoCorners: React.Dispatch<React.SetStateAction<GeoCorners | null>>;
}

export default function EditorSidebar({
  clippedImageBuffer,
  setClippedImageBuffer,
  isLoadingResources,
  pdfUrl,
  clipperRef,
  overlayRef,
  mapRef,
  imageGeoCorners,
  setImageGeoCorners,
}: EditorSidebarProps) {
  if (isLoadingResources) {
    return <LoadingSidebar />;
  }

  if (!pdfUrl) {
    return <PdfSelectSidebar />;
  }
  if (!clippedImageBuffer) {
    return <ClipperSidebar />;
  }
  return (
    <OverlaySidebar
      clippedImageBuffer={clippedImageBuffer}
      setClippedImageBuffer={setClippedImageBuffer}
      overlayRef={overlayRef}
      mapRef={mapRef}
      imageGeoCorners={imageGeoCorners}
      setImageGeoCorners={setImageGeoCorners}
    />
  );
}
