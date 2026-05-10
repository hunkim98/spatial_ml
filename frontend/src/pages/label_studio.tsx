import { GeoCorners } from "@/canvas/overlay/types";
import { ExportResult } from "@/canvas/clipper/controller/exportController";
import LabelEditorComponent from "@/components/editor/canvas/LabelEditorComponent";
import { PDFClipperEditorComponentHandle } from "@/components/editor/canvas/PDFClipperEditorComponent";
import { OverlayEditorComponentHandle } from "@/components/editor/canvas/OverlayEditorComponent";
import LabelSidebar from "@/components/editor/sidebar/LabelSidebar";
import { GeoReferencerHandle } from "@/components/GeoReferencer";
import { Layout } from "@/components/Layout";
import { useLabels } from "@/hooks/useLabels";
import { usePdfs } from "@/hooks/usePdfs";
import { PdfFile } from "@/types/pdf";
import { MapEditorComponentHandle } from "@/components/editor/canvas/MapEditorComponent";
import { Box } from "@mantine/core";
import { useCallback, useRef, useState } from "react";

export default function LabelStudioPage() {
  // ========== Hooks ==========
  const { pdfs, loading: isFetchingAllPDFs } = usePdfs();
  const {
    labels,
    skippedLabels,
    loading: isFetchingAllLabels,
    saveLabel,
    deleteLabel,
    skipLabel,
  } = useLabels();

  // ========== Refs ==========
  const geoReferencerRef = useRef<GeoReferencerHandle>(null);
  const clipperRef = useRef<PDFClipperEditorComponentHandle>(null);
  const overlayRef = useRef<OverlayEditorComponentHandle>(null);
  const mapRef = useRef<MapEditorComponentHandle>(null);
  const [selectedPdf, setSelectedPdf] = useState<PdfFile | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [saving, setSaving] = useState(false);
  const [imageGeoCorners, setImageGeoCorners] = useState<GeoCorners | null>(
    null
  );
  const [clipResult, setClipResult] = useState<ExportResult | null>(null);

  // ========== Derived Values ==========
  const pdfUrl = selectedPdf ? `/api/pdf/${selectedPdf.path}` : null;
  const isLoadingResources = isFetchingAllPDFs || isFetchingAllLabels;

  // ========== Callbacks ==========

  const handlePdfSelect = useCallback(
    (hash: string | null) => {
      const pdf = pdfs.find((p) => p.hash === hash) || null;
      setSelectedPdf(pdf);
      setPageNumber(1);
    },
    [pdfs]
  );

  const handleSaveLabel = useCallback(async () => {
    if (!selectedPdf || !clipResult) return;

    const corners = geoReferencerRef.current?.getCorners();
    if (!corners) {
      console.error("Could not compute corners - PDF not positioned");
      return;
    }

    setSaving(true);
    await saveLabel({
      pdfHash: selectedPdf.hash,
      pdfPath: selectedPdf.path,
      corners: {
        topLeft: corners.corner1,
        topRight: corners.corner2,
        bottomRight: corners.corner4,
        bottomLeft: corners.corner3,
      },
      clipRect: clipResult.clipRect,
      pageNumber,
      clippedImageBuffer: clipResult.buffer,
    });
    setSaving(false);
  }, [selectedPdf, clipResult, pageNumber, saveLabel]);

  const handleDeleteLabel = useCallback(async () => {
    if (!selectedPdf) return;
    await deleteLabel(selectedPdf.hash);
  }, [selectedPdf, deleteLabel]);

  const handleSkip = useCallback(async () => {
    if (!selectedPdf) return;
    await skipLabel(selectedPdf.hash, selectedPdf.path);
    setSelectedPdf(null);
    setClipResult(null);
  }, [selectedPdf, skipLabel]);

  const handleBack = useCallback(() => {
    setSelectedPdf(null);
    setClipResult(null);
  }, []);

  const handleBackToClipper = useCallback(() => {
    setClipResult(null);
    setImageGeoCorners(null);
    mapRef.current?.removeImageLayer();
  }, []);

  return (
    <Layout
      sidebar={
        <LabelSidebar
          pdfs={pdfs}
          labels={labels}
          skippedLabels={skippedLabels}
          onPdfSelect={handlePdfSelect}
          clipResult={clipResult}
          setClipResult={setClipResult}
          isLoadingResources={isLoadingResources}
          pdfUrl={pdfUrl}
          clipperRef={clipperRef}
          overlayRef={overlayRef}
          mapRef={mapRef}
          imageGeoCorners={imageGeoCorners}
          setImageGeoCorners={setImageGeoCorners}
          onSkip={handleSkip}
          onSaveLabel={handleSaveLabel}
          isSaving={saving}
          onBack={handleBack}
          onBackToClipper={handleBackToClipper}
        />
      }
    >
      <Box
        style={{
          width: "100%",
          height: "100%",
          backgroundColor: "#f0f0f0",
        }}
      >
        <LabelEditorComponent
          clipResult={clipResult}
          isLoadingResources={isLoadingResources}
          pdfUrl={pdfUrl}
          pageNumber={pageNumber}
          clipperRef={clipperRef}
          overlayRef={overlayRef}
          mapRef={mapRef}
          imageGeoCorners={imageGeoCorners}
          onImageGeoCornersChange={setImageGeoCorners}
        />
      </Box>
    </Layout>
  );
}

LabelStudioPage.getLayout = (page: React.ReactElement) => page;
