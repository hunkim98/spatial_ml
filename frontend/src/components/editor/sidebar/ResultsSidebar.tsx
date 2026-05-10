import {
  Button,
  Divider,
  Group,
  Paper,
  Slider,
  Stack,
  Switch,
  Text,
  Title,
} from "@mantine/core";
import { IconArrowLeft, IconDownload, IconRefresh } from "@tabler/icons-react";
import { PatternCircle } from "@/canvas/pattern_selector/types";
import { MapEditorComponentHandle } from "../canvas/MapEditorComponent";
import { useCallback, useEffect, useMemo, useState } from "react";

interface ResultsSidebarProps {
  result: GeoJSON.FeatureCollection;
  patterns: PatternCircle[];
  mapRef: React.RefObject<MapEditorComponentHandle | null>;
  isRegenerating: boolean;
  onRegenerateHere: () => void;
  onBackToGeoreference: () => void;
}

export default function ResultsSidebar({
  result,
  patterns,
  mapRef,
  isRegenerating,
  onRegenerateHere,
  onBackToGeoreference,
}: ResultsSidebarProps) {
  const [imageOpacity, setImageOpacity] = useState(50);

  // Zone names from the result
  const zoneNames = useMemo(() => {
    const names = new Set<string>();
    for (const feature of result.features) {
      names.add((feature.properties?.zone as string) ?? "Unknown");
    }
    return [...names].sort();
  }, [result]);

  // Per-zone visibility state — all visible by default
  const [zoneVisibility, setZoneVisibility] = useState<Record<string, boolean>>(
    () => Object.fromEntries(zoneNames.map((name) => [name, true]))
  );

  // Reset visibility state when zone names change
  useEffect(() => {
    setZoneVisibility(
      Object.fromEntries(zoneNames.map((name) => [name, true]))
    );
  }, [zoneNames]);

  // Group features by zone name with counts
  const zoneSummary = useMemo(() => {
    const map: Record<string, number> = {};
    for (const feature of result.features) {
      const name =
        (feature.properties?.zone as string) ?? "Unknown";
      map[name] = (map[name] ?? 0) + 1;
    }
    return Object.entries(map).sort((a, b) => b[1] - a[1]);
  }, [result]);

  // Apply zone filter to map whenever visibility changes
  useEffect(() => {
    const visibleZones = Object.entries(zoneVisibility)
      .filter(([, v]) => v)
      .map(([name]) => name);
    mapRef.current?.setGeoJSONZoneFilter(visibleZones);
  }, [zoneVisibility, mapRef]);

  const handleToggleZone = useCallback((zoneName: string, visible: boolean) => {
    setZoneVisibility((prev) => ({ ...prev, [zoneName]: visible }));
  }, []);

  const handleImageOpacityChange = useCallback(
    (value: number) => {
      setImageOpacity(value);
      if (value === 0) {
        mapRef.current?.hideImageLayer();
      } else {
        mapRef.current?.showImageLayer(value / 100);
        mapRef.current?.setImageLayerOpacity(value / 100);
      }
    },
    [mapRef]
  );

  const handleExport = useCallback(() => {
    const json = JSON.stringify(result, null, 2);
    const blob = new Blob([json], { type: "application/geo+json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "segmentation_result.geojson";
    a.click();
    URL.revokeObjectURL(url);
  }, [result]);

  const allVisible = Object.values(zoneVisibility).every(Boolean);
  const noneVisible = Object.values(zoneVisibility).every((v) => !v);

  const handleToggleAll = useCallback(() => {
    const newValue = !allVisible;
    setZoneVisibility((prev) =>
      Object.fromEntries(Object.keys(prev).map((k) => [k, newValue]))
    );
  }, [allVisible]);

  return (
    <Stack gap="md">
      <Group>
        <Button
          variant="subtle"
          size="compact-sm"
          onClick={onBackToGeoreference}
          p={0}
        >
          <IconArrowLeft size={16} />
        </Button>
        <Title order={5}>Results</Title>
      </Group>

      <Text size="sm" c="dimmed">
        Segmentation complete. {result.features.length} polygon
        {result.features.length !== 1 ? "s" : ""} detected.
      </Text>

      <Stack gap={4}>
        <Text size="sm">Map image opacity</Text>
        <Slider
          value={imageOpacity}
          onChange={handleImageOpacityChange}
          min={0}
          max={100}
          label={(v) => `${v}%`}
          size="sm"
        />
      </Stack>

      <Divider
        label={
          <Group gap={4}>
            <span>Zones ({zoneSummary.length})</span>
            <Button
              variant="subtle"
              size="compact-xs"
              onClick={handleToggleAll}
              p={0}
              fz="xs"
            >
              {allVisible ? "Hide all" : noneVisible ? "Show all" : "Show all"}
            </Button>
          </Group>
        }
        labelPosition="left"
      />

      <Stack gap="xs">
        {zoneSummary.map(([name, count]) => {
          const pattern = patterns.find((p) => p.name === name);
          const color = pattern
            ? `rgb(${pattern.color[0]}, ${pattern.color[1]}, ${pattern.color[2]})`
            : "#888";
          const visible = zoneVisibility[name] ?? true;
          return (
            <Paper key={name} withBorder p="xs">
              <Group gap="xs" wrap="nowrap">
                <Switch
                  checked={visible}
                  onChange={(e) =>
                    handleToggleZone(name, e.currentTarget.checked)
                  }
                  size="xs"
                  color={color}
                />
                <div
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: 4,
                    backgroundColor: color,
                    flexShrink: 0,
                    opacity: visible ? 1 : 0.3,
                  }}
                />
                <Text
                  size="sm"
                  style={{ flex: 1, opacity: visible ? 1 : 0.5 }}
                  lineClamp={1}
                >
                  {name}
                </Text>
                <Text size="xs" c="dimmed">
                  {count}
                </Text>
              </Group>
            </Paper>
          );
        })}
      </Stack>

      {zoneSummary.length === 0 && (
        <Text size="sm" c="dimmed" ta="center" py="xl">
          No zones detected.
        </Text>
      )}

      <Button
        leftSection={<IconRefresh size={16} />}
        onClick={onRegenerateHere}
        loading={isRegenerating}
        variant="light"
        fullWidth
      >
        Regenerate Here
      </Button>

      <Button
        leftSection={<IconDownload size={16} />}
        onClick={handleExport}
        fullWidth
      >
        Export GeoJSON
      </Button>
    </Stack>
  );
}
