import { GeoCorners } from "@/canvas/overlay/types";
import EditorComponent from "@/components/editor/canvas/EditorComponent";
import { ClipperEditorComponentHandle } from "@/components/editor/canvas/ClipperEditorComponent";
import { OverlayEditorComponentHandle } from "@/components/editor/canvas/OverlayEditorComponent";
import { PdfSelectSidebar } from "@/components/editor/PDFSelectSidebar";
import EditorSidebar from "@/components/editor/sidebar/EditorSidebar";
import { GeoReferencerHandle } from "@/components/GeoReferencer";
import { Layout } from "@/components/Layout";
import { useLabels } from "@/hooks/useLabels";
import { usePdfs } from "@/hooks/usePdfs";
import { PdfFile } from "@/types/pdf";
import { MapEditorComponentHandle } from "@/components/editor/canvas/MapEditorComponent";
import { Box, Loader } from "@mantine/core";
import { useCallback, useEffect, useRef, useState } from "react";

export default function StudioPage() {
  // ========== Hooks ==========
  const { pdfs, loading: isFetchingAllPDFs } = usePdfs();
  const {
    labels,
    loading: isFetchingAllLabels,
    saveLabel,
    deleteLabel,
  } = useLabels();

  // ========== Refs ==========
  const geoReferencerRef = useRef<GeoReferencerHandle>(null);
  const clipperRef = useRef<ClipperEditorComponentHandle>(null);
  const overlayRef = useRef<OverlayEditorComponentHandle>(null);
  const mapRef = useRef<MapEditorComponentHandle>(null);
  const [selectedPdf, setSelectedPdf] = useState<PdfFile | null>(null);
  const [pageNumber, setPageNumber] = useState(1); // we will default to page 1
  const [saving, setSaving] = useState(false);
  const [imageGeoCorners, setImageGeoCorners] = useState<GeoCorners | null>(null);
  const [clippedImageBuffer, setClippedImageBuffer] =
    useState<HTMLCanvasElement | null>(null);

  // ========== Effects ==========
  // TEMPORARY: Use test image for overlay editor testing
  useEffect(() => {
    if (!selectedPdf) {
      // Create a mock PDF entry for the test image
      setSelectedPdf({
        hash: "test-anniston",
        path: "test/anniston-test.png",
        name: "anniston-test.png",
        state: "Alabama",
        city: "Anniston",
      });
    }
  }, [selectedPdf]);

  // ========== Derived Values ==========
  // TEMPORARY: Use direct image URL for testing
  const pdfUrl = selectedPdf ? "/anniston-test.png" : null;
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

  const handlePageChange = useCallback((page: number) => {
    setPageNumber(page);
  }, []);

  const handleLocationSelect = useCallback(
    (bounds: [number, number, number, number]) => {
      geoReferencerRef.current?.fitBounds(bounds);
    },
    []
  );

  const handleSaveLabel = useCallback(async () => {
    if (!selectedPdf) return;

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
    });
    setSaving(false);
  }, [selectedPdf, saveLabel]);

  const handleDeleteLabel = useCallback(async () => {
    if (!selectedPdf) return;
    await deleteLabel(selectedPdf.hash);
  }, [selectedPdf, deleteLabel]);

  return (
    <Layout
      sidebar={
        <EditorSidebar
          clippedImageBuffer={clippedImageBuffer}
          setClippedImageBuffer={setClippedImageBuffer}
          isLoadingResources={isLoadingResources}
          pdfUrl={pdfUrl}
          clipperRef={clipperRef}
          overlayRef={overlayRef}
          mapRef={mapRef}
          imageGeoCorners={imageGeoCorners}
          setImageGeoCorners={setImageGeoCorners}
        />
      }
    >
      <Box style={{ width: "100%", height: "100%", backgroundColor: "red" }}>
        <EditorComponent
          clippedImageBuffer={clippedImageBuffer}
          setClippedImageBuffer={setClippedImageBuffer}
          isLoadingResources={isLoadingResources}
          pdfUrl={pdfUrl}
          pageNumber={pageNumber}
          clipperRef={clipperRef}
          overlayRef={overlayRef}
          mapRef={mapRef}
        />
      </Box>
    </Layout>
  );
}

StudioPage.getLayout = (page: React.ReactElement) => page;
