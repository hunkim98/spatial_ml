"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Box, Loader } from "@mantine/core";
import { GeoReferencer, GeoReferencerHandle } from "@/components/GeoReferencer";
import { LabellerSidebar } from "@/components/LabellerSidebar";
import { Layout } from "@/components/Layout";
import { usePdfs } from "@/hooks/usePdfs";
import { useLabels } from "@/hooks/useLabels";
import { PdfFile } from "@/types/pdf";
import { EditorProvider } from "@/canvas/overlay/context";
import { GeoCorners } from "@/canvas/overlay/types";

export default function Labeller() {
  // ========== Hooks ==========
  const { pdfs, loading: pdfsLoading } = usePdfs();
  const {
    labels,
    loading: labelsLoading,
    saveLabel,
    deleteLabel,
  } = useLabels();

  // ========== Refs ==========
  const geoReferencerRef = useRef<GeoReferencerHandle>(null);

  // ========== State ==========
  const [selectedPdf, setSelectedPdf] = useState<PdfFile | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [saving, setSaving] = useState(false);
  const [geoCorners, setGeoCorners] = useState<GeoCorners | null>(null);

  // ========== Derived Values ==========
  const pdfUrl = selectedPdf ? `/api/pdf/${selectedPdf.path}` : null;
  const loading = pdfsLoading || labelsLoading;

  // ========== Effects ==========
  // Clear corners when PDF is deselected
  useEffect(() => {
    if (!selectedPdf) {
      setGeoCorners(null);
    }
  }, [selectedPdf]);

  // Subscribe to corners change events
  useEffect(() => {
    const ref = geoReferencerRef.current;
    if (!ref) return;

    const handleCornersChange = (corners: GeoCorners) => {
      setGeoCorners(corners);
    };

    ref.addCornersChangeListener(handleCornersChange);
    return () => {
      ref.removeCornersChangeListener(handleCornersChange);
    };
  }, [selectedPdf]); // Re-subscribe when PDF changes

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

  const handleSave = useCallback(async () => {
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

  const handleDelete = useCallback(async () => {
    if (!selectedPdf) return;
    await deleteLabel(selectedPdf.hash);
  }, [selectedPdf, deleteLabel]);

  // ========== Render ==========

  if (loading) {
    return (
      <Box
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100%",
        }}
      >
        <Loader size="xl" />
      </Box>
    );
  }

  const sidebar = (
    <LabellerSidebar
      pdfs={pdfs}
      labels={labels}
      selectedPdf={selectedPdf}
      saving={saving}
      pageNumber={pageNumber}
      numPages={1}
      geoCorners={geoCorners}
      onPdfSelect={handlePdfSelect}
      onPageChange={handlePageChange}
      onSave={handleSave}
      onDelete={handleDelete}
      onLocationSelect={handleLocationSelect}
    />
  );

  return (
    <EditorProvider>
      <Layout sidebar={sidebar}>
        <Box style={{ width: "100%", height: "100%" }}>
          <GeoReferencer
            ref={geoReferencerRef}
            pdfUrl={pdfUrl}
            pageNumber={pageNumber}
          />
        </Box>
      </Layout>
    </EditorProvider>
  );
}

// Use custom layout
Labeller.getLayout = (page: React.ReactElement) => page;
