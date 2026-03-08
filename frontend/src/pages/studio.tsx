import { GeoCorners } from "@/canvas/overlay/types";
import { ExportResult } from "@/canvas/clipper/controller/exportController";
import EditorComponent from "@/components/editor/canvas/EditorComponent";
import { ClipperEditorComponentHandle } from "@/components/editor/canvas/ClipperEditorComponent";
import { OverlayEditorComponentHandle } from "@/components/editor/canvas/OverlayEditorComponent";
import EditorSidebar from "@/components/editor/sidebar/EditorSidebar";
import { Layout } from "@/components/Layout";
import { useLabels } from "@/hooks/useLabels";
import { usePdfs } from "@/hooks/usePdfs";
import { PdfFile } from "@/types/pdf";
import { MapEditorComponentHandle } from "@/components/editor/canvas/MapEditorComponent";
import { Box } from "@mantine/core";
import { useCallback, useRef, useState } from "react";

export default function StudioPage() {
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
  const clipperRef = useRef<ClipperEditorComponentHandle>(null);
  const overlayRef = useRef<OverlayEditorComponentHandle>(null);
  const mapRef = useRef<MapEditorComponentHandle>(null);
  const [selectedPdf, setSelectedPdf] = useState<PdfFile | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [isSaving, setIsSaving] = useState(false);
  const [imageGeoCorners, setImageGeoCorners] = useState<GeoCorners | null>(
    null
  );
  const [clipResult, setClipResult] = useState<ExportResult | null>(null);
  const [initialBounds, setInitialBounds] = useState<
    [[number, number], [number, number]] | undefined
  >(undefined);
  const [initialImage, setInitialImage] = useState<
    { url: string; corners: GeoCorners; opacity?: number } | undefined
  >(undefined);
  const [initialClipRect, setInitialClipRect] = useState<
    { x: number; y: number; width: number; height: number } | undefined
  >(undefined);

  // ========== Derived Values ==========
  const pdfUrl = selectedPdf ? `/api/pdf/${selectedPdf.path}` : null;
  const isLoadingResources = isFetchingAllPDFs || isFetchingAllLabels;

  // ========== Callbacks ==========

  const handleBack = useCallback(() => {
    setSelectedPdf(null);
    setClipResult(null);
    setImageGeoCorners(null);
    setInitialBounds(undefined);
    setInitialImage(undefined);
    setInitialClipRect(undefined);
  }, []);

  const handleBackToClipper = useCallback(() => {
    setInitialClipRect(clipResult?.clipRect);
    setClipResult(null);
    setImageGeoCorners(null);
    setInitialBounds(undefined);
    setInitialImage(undefined);
    mapRef.current?.removeImageLayer();
  }, [clipResult]);

  const handlePdfSelect = useCallback(
    (hash: string | null) => {
      const pdf = pdfs.find((p) => p.hash === hash) || null;
      setSelectedPdf(pdf);
      setPageNumber(1);
      setInitialBounds(undefined);
      setInitialImage(undefined);

      // If this PDF already has a label, restore clip result and geo corners
      if (hash && labels[hash]) {
        const label = labels[hash];
        const corners: GeoCorners = {
          corner1: label.corners.topLeft,
          corner2: label.corners.topRight,
          corner3: label.corners.bottomLeft,
          corner4: label.corners.bottomRight,
        };
        setImageGeoCorners(corners);
        const lngs = [corners.corner1.lng, corners.corner2.lng, corners.corner3.lng, corners.corner4.lng];
        const lats = [corners.corner1.lat, corners.corner2.lat, corners.corner3.lat, corners.corner4.lat];
        setInitialBounds([
          [Math.min(...lngs), Math.min(...lats)],
          [Math.max(...lngs), Math.max(...lats)],
        ]);
        setInitialImage({
          url: label.clippedImageUrl,
          corners,
          opacity: 0.7,
        });

        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => {
          const canvas = document.createElement("canvas");
          canvas.width = img.width;
          canvas.height = img.height;
          const ctx = canvas.getContext("2d");
          ctx?.drawImage(img, 0, 0);
          setClipResult({
            buffer: canvas,
            width: img.width,
            height: img.height,
            clipRect: {
              x: label.clipRect.offsetX,
              y: label.clipRect.offsetY,
              width: label.clipRect.width,
              height: label.clipRect.height,
            },
          });
        };
        img.src = label.clippedImageUrl;
      }
    },
    [pdfs, labels]
  );

  const handleSaveLabel = useCallback(async () => {
    if (!selectedPdf || !clipResult || !imageGeoCorners) return;

    setIsSaving(true);
    await saveLabel({
      pdfHash: selectedPdf.hash,
      pdfPath: selectedPdf.path,
      corners: {
        topLeft: imageGeoCorners.corner1,
        topRight: imageGeoCorners.corner2,
        bottomRight: imageGeoCorners.corner4,
        bottomLeft: imageGeoCorners.corner3,
      },
      clipRect: clipResult.clipRect,
      pageNumber,
      clippedImageBuffer: clipResult.buffer,
    });
    setIsSaving(false);

    // Reset state after saving
    setImageGeoCorners(null);
    mapRef.current?.removeImageLayer();
    setClipResult(null);
    setSelectedPdf(null);
  }, [selectedPdf, clipResult, imageGeoCorners, pageNumber, saveLabel]);

  const handleDeleteLabel = useCallback(async () => {
    if (!selectedPdf) return;
    await deleteLabel(selectedPdf.hash);
  }, [selectedPdf, deleteLabel]);

  const handleSkipLabel = useCallback(async () => {
    if (!selectedPdf) return;
    await skipLabel(selectedPdf.hash, selectedPdf.path);
    setSelectedPdf(null);
    setClipResult(null);
  }, [selectedPdf, skipLabel]);

  return (
    <Layout
      sidebar={
        <EditorSidebar
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
          onSkip={handleSkipLabel}
          onSaveLabel={handleSaveLabel}
          isSaving={isSaving}
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
        <EditorComponent
          clipResult={clipResult}
          isLoadingResources={isLoadingResources}
          pdfUrl={pdfUrl}
          pageNumber={pageNumber}
          clipperRef={clipperRef}
          overlayRef={overlayRef}
          mapRef={mapRef}
          imageGeoCorners={imageGeoCorners}
          onImageGeoCornersChange={setImageGeoCorners}
          initialBounds={initialBounds}
          initialImage={initialImage}
          initialClipRect={initialClipRect}
        />
      </Box>
    </Layout>
  );
}

StudioPage.getLayout = (page: React.ReactElement) => page;
