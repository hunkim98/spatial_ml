"use client";

import { useState, useRef, useEffect } from "react";
import { Box, Stack, Text, Button, Paper, Group, Title } from "@mantine/core";
import { IconCopy, IconCheck } from "@tabler/icons-react";
import { GeoReferencer, GeoReferencerHandle } from "@/components/GeoReferencer";
import { Layout } from "@/components/Layout";
import { EditorProvider } from "@/canvas/overlay/context";
import { GeoCorners } from "@/canvas/overlay/types";

export default function TestPosition() {
  const geoReferencerRef = useRef<GeoReferencerHandle>(null);
  const [geoCorners, setGeoCorners] = useState<GeoCorners | null>(null);
  const [copied, setCopied] = useState(false);

  // Poll for corner updates
  useEffect(() => {
    const interval = setInterval(() => {
      const corners = geoReferencerRef.current?.getCorners();
      if (corners) {
        setGeoCorners(corners);
      }
    }, 500);

    return () => clearInterval(interval);
  }, []);

  const handleCopy = () => {
    if (!geoCorners) return;

    const json = JSON.stringify(
      {
        topLeft: {
          lng: Number(geoCorners.corner1.lng.toFixed(6)),
          lat: Number(geoCorners.corner1.lat.toFixed(6)),
        },
        topRight: {
          lng: Number(geoCorners.corner2.lng.toFixed(6)),
          lat: Number(geoCorners.corner2.lat.toFixed(6)),
        },
        bottomRight: {
          lng: Number(geoCorners.corner4.lng.toFixed(6)),
          lat: Number(geoCorners.corner4.lat.toFixed(6)),
        },
        bottomLeft: {
          lng: Number(geoCorners.corner3.lng.toFixed(6)),
          lat: Number(geoCorners.corner3.lat.toFixed(6)),
        },
      },
      null,
      2
    );
    navigator.clipboard.writeText(json);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const sidebar = (
    <Stack gap="md" p="md">
      <Title order={5}>Position Anniston PDF</Title>
      <Text size="sm" c="dimmed">
        1. Draw bounds by clicking and dragging on the map
      </Text>
      <Text size="sm" c="dimmed">
        2. Drag to position and resize to align with the satellite imagery
      </Text>
      <Text size="sm" c="dimmed">
        3. Copy the coordinates below when done
      </Text>

      {geoCorners && (
        <>
          <Paper withBorder p="md" bg="dark.7">
            <Stack gap="xs">
              <Group justify="space-between">
                <Text size="sm" fw={500}>
                  Coordinates
                </Text>
                <Button
                  size="compact-sm"
                  variant={copied ? "filled" : "light"}
                  color={copied ? "green" : "blue"}
                  leftSection={
                    copied ? <IconCheck size={14} /> : <IconCopy size={14} />
                  }
                  onClick={handleCopy}
                >
                  {copied ? "Copied!" : "Copy JSON"}
                </Button>
              </Group>
              <Text size="xs" ff="monospace" style={{ whiteSpace: "pre-wrap" }}>
                TL: {geoCorners.corner1.lng.toFixed(6)},{" "}
                {geoCorners.corner1.lat.toFixed(6)}
                {"\n"}TR: {geoCorners.corner2.lng.toFixed(6)},{" "}
                {geoCorners.corner2.lat.toFixed(6)}
                {"\n"}BR: {geoCorners.corner4.lng.toFixed(6)},{" "}
                {geoCorners.corner4.lat.toFixed(6)}
                {"\n"}BL: {geoCorners.corner3.lng.toFixed(6)},{" "}
                {geoCorners.corner3.lat.toFixed(6)}
              </Text>
            </Stack>
          </Paper>
        </>
      )}

      {!geoCorners && (
        <Paper withBorder p="md" bg="dark.8">
          <Text size="sm" c="dimmed" ta="center">
            Draw bounds on the map to see coordinates
          </Text>
        </Paper>
      )}
    </Stack>
  );

  return (
    <EditorProvider>
      <Layout sidebar={sidebar}>
        <Box style={{ width: "100%", height: "100%" }}>
          <GeoReferencer
            ref={geoReferencerRef}
            pdfUrl="/2024-Zoning-Map.pdf"
            initialCenter={{ lng: -85.8316, lat: 33.6598 }}
          />
        </Box>
      </Layout>
    </EditorProvider>
  );
}

// Use custom layout
TestPosition.getLayout = (page: React.ReactElement) => page;
