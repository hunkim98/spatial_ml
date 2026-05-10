import { useCallback, useEffect, useRef, useState } from "react";
import {
  Box,
  Button,
  Divider,
  Loader,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconDownload } from "@tabler/icons-react";
import { Layout } from "@/components/Layout";
import PolygonEditorComponent from "@/components/editor/canvas/PolygonEditorComponent";
import { MapEditorComponentHandle } from "@/components/editor/canvas/MapEditorComponent";

// Cambridge, MA zoning data copied from data/maps/MA/cambridge/geojson/
const TEST_GEOJSON_URL = "/test-polygons.geojson";

export default function PolygonEditTest() {
  const mapRef = useRef<MapEditorComponentHandle>(null);

  const [geojsonData, setGeojsonData] =
    useState<GeoJSON.FeatureCollection | null>(null);
  const [loading, setLoading] = useState(true);
  const [bounds, setBounds] = useState<
    [[number, number], [number, number]] | undefined
  >(undefined);

  // Fetch GeoJSON on mount, compute bounding box
  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      try {
        const res = await fetch(TEST_GEOJSON_URL);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const raw: GeoJSON.FeatureCollection = await res.json();
        if (cancelled) return;

        // Normalize: map ZONE_TYPE → zone so overlay rendering picks it up
        const data: GeoJSON.FeatureCollection = {
          ...raw,
          features: raw.features.map((f) => ({
            ...f,
            properties: {
              ...f.properties,
              zone: f.properties?.ZONE_TYPE ?? f.properties?.zone ?? "Unknown",
            },
          })),
        };

        // Compute tight bounding box from all coordinates
        let minLng = Infinity,
          minLat = Infinity,
          maxLng = -Infinity,
          maxLat = -Infinity;

        for (const feature of data.features) {
          const geom = feature.geometry;
          if (geom.type !== "Polygon" && geom.type !== "MultiPolygon") continue;
          const rings =
            geom.type === "Polygon"
              ? geom.coordinates
              : geom.coordinates.flat();
          for (const ring of rings) {
            for (const [lng, lat] of ring) {
              if (lng < minLng) minLng = lng;
              if (lng > maxLng) maxLng = lng;
              if (lat < minLat) minLat = lat;
              if (lat > maxLat) maxLat = lat;
            }
          }
        }

        if (isFinite(minLng)) {
          setBounds([
            [minLng, minLat],
            [maxLng, maxLat],
          ]);
        }

        setGeojsonData(data);
        setLoading(false);
      } catch (err) {
        console.error("Failed to fetch GeoJSON:", err);
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    return () => {
      cancelled = true;
    };
  }, []);

  // Add GeoJSON to MapLibre and zoom to bounds once data + map are ready
  useEffect(() => {
    if (!geojsonData || !bounds) return;

    const interval = setInterval(() => {
      const map = mapRef.current;
      if (!map) return;

      map.addGeoJSONLayer(geojsonData);
      map.getMapRef()?.fitBounds(bounds, { padding: 40 });
      clearInterval(interval);
    }, 100);

    return () => clearInterval(interval);
  }, [geojsonData, bounds]);

  const handleGeoJSONChange = useCallback(
    (geojson: GeoJSON.FeatureCollection) => {
      setGeojsonData(geojson);
    },
    []
  );

  const handleExport = useCallback(() => {
    if (!geojsonData) return;
    const json = JSON.stringify(geojsonData, null, 2);
    const blob = new Blob([json], { type: "application/geo+json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "edited-polygons.geojson";
    a.click();
    URL.revokeObjectURL(url);
  }, [geojsonData]);

  const featureCount = geojsonData?.features.length ?? 0;

  const sidebar = (
    <Stack gap="md">
      <Title order={5}>Polygon Edit Test</Title>
      <Text size="xs" c="dimmed">
        Cambridge, MA — test polygon editing on the overlay canvas.
      </Text>

      <Divider />

      {loading ? (
        <Stack align="center" py="xl">
          <Loader size="sm" />
          <Text size="sm" c="dimmed">
            Loading GeoJSON...
          </Text>
        </Stack>
      ) : (
        <>
          <Text size="sm">
            {featureCount} polygon{featureCount !== 1 ? "s" : ""} loaded
          </Text>

          <Button
            leftSection={<IconDownload size={16} />}
            onClick={handleExport}
            fullWidth
            disabled={!geojsonData}
          >
            Export GeoJSON
          </Button>

          <Divider label="Controls" labelPosition="center" />

          <Stack gap={4}>
            <Text size="xs" c="dimmed">
              Click polygon to select, see vertex handles
            </Text>
            <Text size="xs" c="dimmed">
              Click + drag vertex to reshape
            </Text>
            <Text size="xs" c="dimmed">
              Delete / Backspace to remove vertex or polygon
            </Text>
            <Text size="xs" c="dimmed">
              Escape to deselect
            </Text>
            <Text size="xs" c="dimmed">
              Space + drag to pan map
            </Text>
          </Stack>
        </>
      )}
    </Stack>
  );

  return (
    <Layout sidebar={sidebar}>
      <Box style={{ width: "100%", height: "100%", backgroundColor: "#f0f0f0" }}>
        {geojsonData && (
          <PolygonEditorComponent
            mapRef={mapRef}
            geojson={geojsonData}
            onGeoJSONChange={handleGeoJSONChange}
            initialBounds={bounds}
          />
        )}
      </Box>
    </Layout>
  );
}

PolygonEditTest.getLayout = (page: React.ReactElement) => page;
