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
  Paper,
  ScrollArea,
  Divider,
  Slider,
  Loader,
  Switch,
} from "@mantine/core";
import { IconDownload } from "@tabler/icons-react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Layout } from "@/components/Layout";
import {
  ANNISTON_CENTER,
  ANNISTON_BOUNDS,
  ZONE_TYPES,
  ANNISTON_GEOJSON_URL,
  ANNISTON_PDF,
  ZoneInfo,
  getZoneInfo,
} from "@/data/anniston-demo";

interface SelectedFeature {
  zone: string;
  zoneInfo: ZoneInfo | null;
  properties: Record<string, unknown>;
}

// Sample georeferenced corners for the PDF (these would come from the labeller in real use)
// Format: [topLeft, topRight, bottomRight, bottomLeft] as [lng, lat]
const PDF_CORNERS: [[number, number], [number, number], [number, number], [number, number]] = [
  [-85.875, 33.735],  // top-left
  [-85.765, 33.735],  // top-right
  [-85.765, 33.615],  // bottom-right
  [-85.875, 33.615],  // bottom-left
];

export default function DemoViewer() {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [selectedFeature, setSelectedFeature] = useState<SelectedFeature | null>(null);
  const [hoveredZone, setHoveredZone] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [featureCount, setFeatureCount] = useState(0);
  const [polygonOpacity, setPolygonOpacity] = useState(0.6);
  const [pdfOpacity, setPdfOpacity] = useState(0.5);
  const [showPdf, setShowPdf] = useState(true);
  const [geojsonData, setGeojsonData] = useState<GeoJSON.FeatureCollection | null>(null);

  // Initialize map
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
      // Add PDF as image source (georeferenced)
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

      // Fetch real GeoJSON
      try {
        const response = await fetch(ANNISTON_GEOJSON_URL);
        if (!response.ok) throw new Error("Failed to fetch GeoJSON");

        const data: GeoJSON.FeatureCollection = await response.json();

        // Add IDs to features for hover state
        data.features = data.features.map((f, i) => ({ ...f, id: i }));

        setGeojsonData(data);
        setFeatureCount(data.features.length);

        // Add zoning polygons source
        map.addSource("zones", {
          type: "geojson",
          data: data,
        });

        // Build color match expression from real zone values
        const colorMatch: maplibregl.ExpressionSpecification = [
          "match",
          ["get", "Zone_2024"],
          "C: Urban Core", ZONE_TYPES["C: Urban Core"].color,
          "UC1: Urban Center 1", ZONE_TYPES["UC1: Urban Center 1"].color,
          "UC2: Urban Center 2", ZONE_TYPES["UC2: Urban Center 2"].color,
          "UN1: Urban Neighborhood 1", ZONE_TYPES["UN1: Urban Neighborhood 1"].color,
          "UN2: Urban Neighborhood 2", ZONE_TYPES["UN2: Urban Neighborhood 2"].color,
          "SN1: Suburban Neighborhood 1", ZONE_TYPES["SN1: Suburban Neighborhood 1"].color,
          "SN2: Suburban Neighborhood 2", ZONE_TYPES["SN2: Suburban Neighborhood 2"].color,
          "SNC: Suburban Neighborhood Center", ZONE_TYPES["SNC: Suburban Neighborhood Center"].color,
          "SC: Suburban Corridor", ZONE_TYPES["SC: Suburban Corridor"].color,
          "SE: Suburban Edge", ZONE_TYPES["SE: Suburban Edge"].color,
          "MI: Major Institution/Civic Campus", ZONE_TYPES["MI: Major Institution/Civic Campus"].color,
          "MI: Major UC2: Urban Center 2", ZONE_TYPES["MI: Major UC2: Urban Center 2"].color,
          "IL: Industrial Limited", ZONE_TYPES["IL: Industrial Limited"].color,
          "IG: Industrial General", ZONE_TYPES["IG: Industrial General"].color,
          "NO: Natural/Open Space", ZONE_TYPES["NO: Natural/Open Space"].color,
          "#888888", // default
        ];

        // Add fill layer
        map.addLayer({
          id: "zones-fill",
          type: "fill",
          source: "zones",
          paint: {
            "fill-color": colorMatch,
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
          id: "zones-outline",
          type: "line",
          source: "zones",
          paint: {
            "line-color": "#333333",
            "line-width": [
              "case",
              ["boolean", ["feature-state", "hover"], false],
              2,
              0.5,
            ],
          },
        });

        // Click handler
        map.on("click", "zones-fill", (e) => {
          if (e.features && e.features.length > 0) {
            const feature = e.features[0];
            const zone = feature.properties?.Zone_2024 as string;
            const zoneInfo = getZoneInfo(zone);

            setSelectedFeature({
              zone,
              zoneInfo,
              properties: feature.properties || {},
            });
          }
        });

        // Hover effects
        let hoveredId: string | number | null = null;

        map.on("mousemove", "zones-fill", (e) => {
          if (e.features && e.features.length > 0) {
            if (hoveredId !== null) {
              map.setFeatureState({ source: "zones", id: hoveredId }, { hover: false });
            }
            hoveredId = e.features[0].id ?? null;
            if (hoveredId !== null) {
              map.setFeatureState({ source: "zones", id: hoveredId }, { hover: true });
            }
            setHoveredZone(e.features[0].properties?.Zone_2024 || null);
            map.getCanvas().style.cursor = "pointer";
          }
        });

        map.on("mouseleave", "zones-fill", () => {
          if (hoveredId !== null) {
            map.setFeatureState({ source: "zones", id: hoveredId }, { hover: false });
          }
          hoveredId = null;
          setHoveredZone(null);
          map.getCanvas().style.cursor = "";
        });

        setLoading(false);
      } catch (error) {
        console.error("Failed to load GeoJSON:", error);
        setLoading(false);
      }
    });

    // Fit to bounds
    map.fitBounds(ANNISTON_BOUNDS, { padding: 50 });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update polygon opacity
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("zones-fill")) return;

    map.setPaintProperty("zones-fill", "fill-opacity", [
      "case",
      ["boolean", ["feature-state", "hover"], false],
      Math.min(polygonOpacity + 0.2, 1),
      polygonOpacity,
    ]);
  }, [polygonOpacity]);

  // Update PDF opacity and visibility
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("pdf-layer")) return;

    map.setPaintProperty("pdf-layer", "raster-opacity", showPdf ? pdfOpacity : 0);
  }, [pdfOpacity, showPdf]);

  const handleExport = useCallback(() => {
    if (!geojsonData) return;

    const dataStr = JSON.stringify(geojsonData, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "anniston-zoning.geojson";
    a.click();
    URL.revokeObjectURL(url);
  }, [geojsonData]);

  const sidebar = (
    <Stack gap="md">
      <Title order={5}>Anniston, AL</Title>
      <Text size="xs" c="dimmed">Zoning Map Viewer</Text>

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

      {/* Polygon Opacity Control */}
      <Card padding="sm" withBorder>
        <Text size="sm" fw={500} mb="xs">
          Polygon Opacity
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

      {/* Selected Feature Info */}
      {selectedFeature ? (
        <Card padding="sm" withBorder>
          <Group gap="xs" mb="xs">
            {selectedFeature.zoneInfo && (
              <Box
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: 4,
                  backgroundColor: selectedFeature.zoneInfo.color,
                }}
              />
            )}
            <Text fw={600}>{selectedFeature.zoneInfo?.code || "Unknown"}</Text>
          </Group>
          <Text size="sm" fw={500}>
            {selectedFeature.zoneInfo?.name || selectedFeature.zone}
          </Text>
          {selectedFeature.zoneInfo && (
            <Text size="xs" c="dimmed" mt="xs">
              {selectedFeature.zoneInfo.description}
            </Text>
          )}
          {typeof selectedFeature.properties.STREET_ADD === "string" &&
            selectedFeature.properties.STREET_ADD.trim() && (
            <Text size="xs" mt="xs">
              Address: {selectedFeature.properties.STREET_ADD}
            </Text>
          )}
        </Card>
      ) : (
        <Text size="sm" c="dimmed">
          Click on a parcel to see details
        </Text>
      )}

      <Divider label="Zone Legend" labelPosition="center" />

      {/* Zone Legend */}
      <ScrollArea h={250}>
        <Stack gap="xs">
          {Object.entries(ZONE_TYPES).map(([key, zone]) => (
            <Paper
              key={key}
              p="xs"
              withBorder
              style={{
                opacity: hoveredZone && hoveredZone !== key ? 0.5 : 1,
                transition: "opacity 0.2s",
              }}
            >
              <Group gap="xs">
                <Box
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: 4,
                    backgroundColor: zone.color,
                    flexShrink: 0,
                  }}
                />
                <div style={{ minWidth: 0 }}>
                  <Text size="sm" fw={500}>
                    {zone.code}
                  </Text>
                  <Text size="xs" c="dimmed" truncate>
                    {zone.name}
                  </Text>
                </div>
              </Group>
            </Paper>
          ))}
        </Stack>
      </ScrollArea>

      <Divider />

      {/* Export Button */}
      <Button
        variant="light"
        color="green"
        leftSection={<IconDownload size={16} />}
        onClick={handleExport}
        disabled={!geojsonData}
      >
        Export GeoJSON
      </Button>

      <Text size="xs" c="dimmed">
        {featureCount.toLocaleString()} parcels loaded
      </Text>
    </Stack>
  );

  return (
    <Layout sidebar={sidebar}>
      <Box style={{ width: "100%", height: "100%", position: "relative" }}>
        <div ref={mapContainerRef} style={{ width: "100%", height: "100%" }} />

        {/* Loading overlay */}
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
            <Text c="white">Loading zoning data...</Text>
          </Box>
        )}
      </Box>
    </Layout>
  );
}

// Use custom layout
DemoViewer.getLayout = (page: React.ReactElement) => page;
