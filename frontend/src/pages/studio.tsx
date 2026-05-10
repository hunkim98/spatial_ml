import { GeoCorners } from "@/canvas/overlay/types";
import { ExportResult } from "@/canvas/clipper/controller/exportController";
import { PatternCircle } from "@/canvas/pattern_selector/types";
import StudioEditorComponent from "@/components/editor/canvas/StudioEditorComponent";
import { ImageClipperEditorComponentHandle } from "@/components/editor/canvas/ImageClipperEditorComponent";
import { PatternSelectorEditorComponentHandle } from "@/components/editor/canvas/PatternSelectorEditorComponent";
import { OverlayEditorComponentHandle } from "@/components/editor/canvas/OverlayEditorComponent";
import { UploadEditorComponentHandle } from "@/components/editor/canvas/UploadEditorComponent";
import { MapEditorComponentHandle } from "@/components/editor/canvas/MapEditorComponent";
import StudioSidebar from "@/components/editor/sidebar/StudioSidebar";
import { Layout } from "@/components/Layout";
import { Box } from "@mantine/core";
import { useCallback, useRef, useState } from "react";
import { useSegmentation } from "@/hooks/useSegmentation";

export default function StudioPage() {
  // ========== Refs ==========
  const uploadRef = useRef<UploadEditorComponentHandle>(null);
  const patternSelectorRef =
    useRef<PatternSelectorEditorComponentHandle>(null);
  const clipperRef = useRef<ImageClipperEditorComponentHandle>(null);
  const overlayRef = useRef<OverlayEditorComponentHandle>(null);
  const mapRef = useRef<MapEditorComponentHandle>(null);

  // ========== Upload state ==========
  const [mapImageFile, setMapImageFile] = useState<File | null>(null);
  const [mapImageUrl, setMapImageUrl] = useState<string | null>(null);
  const [mapImageDimensions, setMapImageDimensions] = useState<{
    width: number;
    height: number;
  } | null>(null);

  // ========== Pattern selection state ==========
  const [patterns, setPatterns] = useState<PatternCircle[]>([]);
  const [patternsConfirmed, setPatternsConfirmed] = useState(false);
  const [patternCrops, setPatternCrops] = useState<Record<string, Blob>>({});

  // ========== Clip state ==========
  const [clipResult, setClipResult] = useState<ExportResult | null>(null);
  const [initialClipRect, setInitialClipRect] = useState<
    { x: number; y: number; width: number; height: number } | undefined
  >(undefined);

  // ========== Georeference state ==========
  const [imageGeoCorners, setImageGeoCorners] = useState<GeoCorners | null>(
    null
  );
  const [initialBounds, setInitialBounds] = useState<
    [[number, number], [number, number]] | undefined
  >(undefined);
  const [initialImage, setInitialImage] = useState<
    { url: string; corners: GeoCorners; opacity?: number } | undefined
  >(undefined);

  // ========== Segmentation ==========
  const segmentation = useSegmentation();
  const [segmentationResult, setSegmentationResult] =
    useState<GeoJSON.FeatureCollection | null>(null);

  // ========== Callbacks ==========

  const handleGeoJSONChange = useCallback(
    (geojson: GeoJSON.FeatureCollection) => {
      setSegmentationResult(geojson);
    },
    []
  );

  const handleImageSelect = useCallback(
    (file: File, url: string, width: number, height: number) => {
      setMapImageFile(file);
      setMapImageUrl(url);
      setMapImageDimensions({ width, height });
    },
    []
  );

  const handleBackToUpload = useCallback(() => {
    if (mapImageUrl) URL.revokeObjectURL(mapImageUrl);
    setMapImageFile(null);
    setMapImageUrl(null);
    setMapImageDimensions(null);
    setPatterns([]);
    setPatternsConfirmed(false);
    setPatternCrops({});
    setClipResult(null);
    setImageGeoCorners(null);
    setInitialBounds(undefined);
    setInitialImage(undefined);
    setInitialClipRect(undefined);
    setSegmentationResult(null);
  }, [mapImageUrl]);

  const handleConfirmPatterns = useCallback(() => {
    // Export all pattern crops before unmounting the pattern selector
    const crops: Record<string, Blob> = {};

    for (const pattern of patterns) {
      const result = patternSelectorRef.current?.exportPatternCrop(pattern.id);
      if (result) {
        // Use toDataURL → fetch → blob (synchronous-like, avoids toBlob callback issues)
        const dataUrl = result.buffer.toDataURL("image/png");
        const binary = atob(dataUrl.split(",")[1]);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }
        crops[pattern.id] = new Blob([bytes], { type: "image/png" });
      }
    }

    if (Object.keys(crops).length === 0) {
      console.warn("No pattern crops exported — check pattern selector ref");
      return;
    }

    setPatternCrops(crops);
    setPatternsConfirmed(true);
  }, [patterns]);

  const handleBackToPatterns = useCallback(() => {
    setPatternsConfirmed(false);
    setPatternCrops({});
    setClipResult(null);
    setImageGeoCorners(null);
    setInitialBounds(undefined);
    setInitialImage(undefined);
    setInitialClipRect(undefined);
    setSegmentationResult(null);
    mapRef.current?.removeGeoJSONLayer();
    mapRef.current?.removeImageLayer();
  }, []);

  const handleBackToClipper = useCallback(() => {
    setInitialClipRect(clipResult?.clipRect);
    setClipResult(null);
    setImageGeoCorners(null);
    setInitialBounds(undefined);
    setInitialImage(undefined);
    setSegmentationResult(null);
    mapRef.current?.removeGeoJSONLayer();
    mapRef.current?.removeImageLayer();
  }, [clipResult]);

  const handleGeneratePolygons = useCallback(async () => {
    if (!clipResult || !imageGeoCorners || patterns.length === 0) return;

    // Convert clipped image to File
    const imageBlob = await new Promise<Blob | null>((resolve) => {
      clipResult.buffer.toBlob((blob) => resolve(blob), "image/png");
    });
    if (!imageBlob) return;
    const imageFile = new File([imageBlob], "map.png", { type: "image/png" });

    // Compute extent from geo corners
    const lngs = [
      imageGeoCorners.corner1.lng,
      imageGeoCorners.corner2.lng,
      imageGeoCorners.corner3.lng,
      imageGeoCorners.corner4.lng,
    ];
    const lats = [
      imageGeoCorners.corner1.lat,
      imageGeoCorners.corner2.lat,
      imageGeoCorners.corner3.lat,
      imageGeoCorners.corner4.lat,
    ];
    const extent = {
      xmin: Math.min(...lngs),
      ymin: Math.min(...lats),
      xmax: Math.max(...lngs),
      ymax: Math.max(...lats),
    };

    // Build pattern array from stored crops
    const patternArray = patterns
      .filter((p) => patternCrops[p.id])
      .map((p) => ({
        name: p.name,
        crop: patternCrops[p.id],
      }));

    if (patternArray.length === 0) {
      console.error("No pattern crops available. patternCrops:", patternCrops);
      return;
    }

    segmentation.mutate(
      { image: imageFile, patterns: patternArray, extent },
      {
        onSuccess: (data) => {
          setSegmentationResult(data);
          mapRef.current?.addGeoJSONLayer(data);
        },
        onError: (err) => console.error("Segmentation failed:", err),
      }
    );
  }, [clipResult, imageGeoCorners, patterns, patternCrops, segmentation]);

  return (
    <Layout
      sidebar={
        <StudioSidebar
          mapImageUrl={mapImageUrl}
          mapImageFile={mapImageFile}
          mapImageDimensions={mapImageDimensions}
          patterns={patterns}
          patternsConfirmed={patternsConfirmed}
          clipResult={clipResult}
          setClipResult={setClipResult}
          uploadRef={uploadRef}
          patternSelectorRef={patternSelectorRef}
          clipperRef={clipperRef}
          overlayRef={overlayRef}
          mapRef={mapRef}
          imageGeoCorners={imageGeoCorners}
          setImageGeoCorners={setImageGeoCorners}
          segmentationResult={segmentationResult}
          isSegmenting={segmentation.isPending}
          onBackToUpload={handleBackToUpload}
          onConfirmPatterns={handleConfirmPatterns}
          onBackToPatterns={handleBackToPatterns}
          onBackToClipper={handleBackToClipper}
          onGeneratePolygons={handleGeneratePolygons}
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
        <StudioEditorComponent
          mapImageUrl={mapImageUrl}
          patternsConfirmed={patternsConfirmed}
          clipResult={clipResult}
          uploadRef={uploadRef}
          patternSelectorRef={patternSelectorRef}
          clipperRef={clipperRef}
          overlayRef={overlayRef}
          mapRef={mapRef}
          imageGeoCorners={imageGeoCorners}
          onImageGeoCornersChange={setImageGeoCorners}
          onImageSelect={handleImageSelect}
          onPatternsChange={setPatterns}
          initialBounds={initialBounds}
          initialImage={initialImage}
          initialClipRect={initialClipRect}
          segmentationResult={segmentationResult}
          onGeoJSONChange={handleGeoJSONChange}
        />
      </Box>
    </Layout>
  );
}

StudioPage.getLayout = (page: React.ReactElement) => page;
