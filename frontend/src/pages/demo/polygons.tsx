"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import {
  Box,
  Card,
  Text,
  Title,
  Stack,
  Group,
  Button,
  Divider,
  Slider,
  Loader,
  Switch,
  ColorSwatch,
} from "@mantine/core";
import { IconDownload } from "@tabler/icons-react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Layout } from "@/components/Layout";
import {
  ANNISTON_CENTER,
  ANNISTON_BOUNDS,
  ANNISTON_GEOJSON_URL,
  ANNISTON_PDF,
} from "@/data/anniston-demo";

// Sample georeferenced corners for the PDF
const PDF_CORNERS: [[number, number], [number, number], [number, number], [number, number]] = [
  [-85.875, 33.735],
  [-85.765, 33.735],
  [-85.765, 33.615],
  [-85.875, 33.615],
];

const POLYGON_COLOR = "#3b82f6"; // Blue color for all polygons

export default function PolygonsViewer() {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [loading, setLoading] = useState(true);
  const [featureCount, setFeatureCount] = useState(0);
  const [polygonOpacity, setPolygonOpacity] = useState(0.4);
  const [pdfOpacity, setPdfOpacity] = useState(0.7);
  const [showPdf, setShowPdf] = useState(true);
  const [showFill, setShowFill] = useState(true);
  const [geojsonData, setGeojsonData] = useState<GeoJSON.FeatureCollection | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          esri: {
            type: "raster",
            tiles: [
              "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
            attribution: "Esri, Maxar, Earthstar Geographics",
          },
        },
        layers: [
          {
            id: "esri-imagery",
            type: "raster",
            source: "esri",
            minzoom: 0,
            maxzoom: 22,
          },
        ],
      },
      center: [ANNISTON_CENTER.lng, ANNISTON_CENTER.lat],
      zoom: 12,
    });

    map.on("load", async () => {
      // Add PDF as image source
      map.addSource("pdf-overlay", {
        type: "image",
        url: ANNISTON_PDF.url,
        coordinates: PDF_CORNERS,
      });

      map.addLayer({
        id: "pdf-layer",
        type: "raster",
        source: "pdf-overlay",
        paint: {
          "raster-opacity": pdfOpacity,
        },
      });

      // Fetch GeoJSON
      try {
        const response = await fetch(ANNISTON_GEOJSON_URL);
        if (!response.ok) throw new Error("Failed to fetch GeoJSON");

        const data: GeoJSON.FeatureCollection = await response.json();
        data.features = data.features.map((f, i) => ({ ...f, id: i }));

        setGeojsonData(data);
        setFeatureCount(data.features.length);

        map.addSource("polygons", {
          type: "geojson",
          data: data,
        });

        // Add fill layer - single color for all polygons
        map.addLayer({
          id: "polygons-fill",
          type: "fill",
          source: "polygons",
          paint: {
            "fill-color": POLYGON_COLOR,
            "fill-opacity": [
              "case",
              ["boolean", ["feature-state", "hover"], false],
              polygonOpacity + 0.2,
              polygonOpacity,
            ],
          },
        });

        // Add outline layer
        map.addLayer({
          id: "polygons-outline",
          type: "line",
          source: "polygons",
          paint: {
            "line-color": "#1e40af",
            "line-width": [
              "case",
              ["boolean", ["feature-state", "hover"], false],
              2,
              0.8,
            ],
          },
        });

        // Hover effects
        let hoveredId: string | number | null = null;

        map.on("mousemove", "polygons-fill", (e) => {
          if (e.features && e.features.length > 0) {
            if (hoveredId !== null) {
              map.setFeatureState({ source: "polygons", id: hoveredId }, { hover: false });
            }
            hoveredId = e.features[0].id ?? null;
            if (hoveredId !== null) {
              map.setFeatureState({ source: "polygons", id: hoveredId }, { hover: true });
            }
            map.getCanvas().style.cursor = "pointer";
          }
        });

        map.on("mouseleave", "polygons-fill", () => {
          if (hoveredId !== null) {
            map.setFeatureState({ source: "polygons", id: hoveredId }, { hover: false });
          }
          hoveredId = null;
          map.getCanvas().style.cursor = "";
        });

        setLoading(false);
      } catch (error) {
        console.error("Failed to load GeoJSON:", error);
        setLoading(false);
      }
    });

    map.fitBounds(ANNISTON_BOUNDS, { padding: 50 });
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update polygon opacity and fill visibility
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("polygons-fill")) return;

    map.setPaintProperty("polygons-fill", "fill-opacity", [
      "case",
      ["boolean", ["feature-state", "hover"], false],
      showFill ? Math.min(polygonOpacity + 0.2, 1) : 0,
      showFill ? polygonOpacity : 0,
    ]);
  }, [polygonOpacity, showFill]);

  // Update PDF opacity and visibility
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("pdf-layer")) return;

    map.setPaintProperty("pdf-layer", "raster-opacity", showPdf ? pdfOpacity : 0);
  }, [pdfOpacity, showPdf]);

  const handleExport = useCallback(() => {
    if (!geojsonData) return;

    // Export without zone data - just geometries
    const cleanData: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: geojsonData.features.map((f) => ({
        type: "Feature" as const,
        geometry: f.geometry,
        properties: {
          id: f.id,
        },
      })),
    };

    const dataStr = JSON.stringify(cleanData, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "anniston-polygons.geojson";
    a.click();
    URL.revokeObjectURL(url);
  }, [geojsonData]);

  const sidebar = (
    <Stack gap="md">
      <Title order={5}>Anniston, AL</Title>
      <Text size="xs" c="dimmed">Extracted Polygons (Unlabeled)</Text>

      <Divider />

      {/* PDF Overlay Controls */}
      <Card padding="sm" withBorder>
        <Group justify="space-between" mb="xs">
          <Text size="sm" fw={500}>
            PDF Overlay
          </Text>
          <Switch
            size="xs"
            checked={showPdf}
            onChange={(e) => setShowPdf(e.currentTarget.checked)}
          />
        </Group>
        {showPdf && (
          <>
            <Text size="xs" c="dimmed" mb="xs">
              Opacity
            </Text>
            <Slider
              value={pdfOpacity}
              onChange={setPdfOpacity}
              min={0}
              max={1}
              step={0.1}
              size="sm"
              marks={[
                { value: 0, label: "0%" },
                { value: 0.5, label: "50%" },
                { value: 1, label: "100%" },
              ]}
            />
          </>
        )}
      </Card>

      {/* Polygon Controls */}
      <Card padding="sm" withBorder>
        <Group justify="space-between" mb="xs">
          <Group gap="xs">
            <Text size="sm" fw={500}>
              Polygons
            </Text>
            <ColorSwatch color={POLYGON_COLOR} size={14} />
          </Group>
          <Switch
            size="xs"
            checked={showFill}
            onChange={(e) => setShowFill(e.currentTarget.checked)}
            label="Fill"
            labelPosition="left"
            styles={{ label: { fontSize: 12, paddingRight: 4 } }}
          />
        </Group>
        <Text size="xs" c="dimmed" mb="xs">
          Opacity
        </Text>
        <Slider
          value={polygonOpacity}
          onChange={setPolygonOpacity}
          min={0}
          max={1}
          step={0.1}
          size="sm"
          marks={[
            { value: 0, label: "0%" },
            { value: 0.5, label: "50%" },
            { value: 1, label: "100%" },
          ]}
        />
      </Card>

      <Divider />

      <Card padding="sm" withBorder bg="gray.0">
        <Text size="sm" fw={500} mb="xs">
          Status
        </Text>
        <Text size="xs" c="dimmed">
          These polygons have been extracted from the zoning map but have not yet been labeled with zone types.
        </Text>
      </Card>

      <Divider />

      {/* Export Button */}
      <Button
        variant="light"
        color="blue"
        leftSection={<IconDownload size={16} />}
        onClick={handleExport}
        disabled={!geojsonData}
      >
        Export Polygons
      </Button>

      <Text size="xs" c="dimmed">
        {featureCount.toLocaleString()} polygons
      </Text>
    </Stack>
  );

  return (
    <Layout sidebar={sidebar}>
      <Box style={{ width: "100%", height: "100%", position: "relative" }}>
        <div ref={mapContainerRef} style={{ width: "100%", height: "100%" }} />

        {loading && (
          <Box
            style={{
              position: "absolute",
              inset: 0,
              background: "rgba(0,0,0,0.5)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              alignItems: "center",
              gap: 16,
            }}
          >
            <Loader size="lg" color="white" />
            <Text c="white">Loading polygons...</Text>
          </Box>
        )}
      </Box>
    </Layout>
  );
}

PolygonsViewer.getLayout = (page: React.ReactElement) => page;
