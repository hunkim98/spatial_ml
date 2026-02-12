import { useState } from "react";
import {
  Stack,
  Title,
  Select,
  TextInput,
  Button,
  Group,
  Text,
  Badge,
  Divider,
  Paper,
  Loader,
} from "@mantine/core";
import {
  IconSearch,
  IconTrash,
  IconDeviceFloppy,
  IconCopy,
} from "@tabler/icons-react";
import { useDebouncedCallback } from "@mantine/hooks";
import { PdfFile } from "@/types/pdf";
import { GeoLabel } from "@/types/db";
import { useLocationSearch } from "@/hooks/useLocationSearch";
import { GeoCorners } from "@/canvas/overlay/types";

interface PdfSelectSidebarProps {
  pdfs: PdfFile[];
  labels: Record<string, GeoLabel>;
  selectedPdf: PdfFile | null;
  saving: boolean;
  pageNumber: number;
  numPages: number;
  geoCorners: GeoCorners | null;
  onPdfSelect: (hash: string | null) => void;
  onPageChange: (page: number) => void;
  onSave: () => void;
  onDelete: () => void;
  onLocationSelect: (bounds: [number, number, number, number]) => void;
}

export function PdfSelectSidebar({
  pdfs,
  labels,
  selectedPdf,
  saving,
  pageNumber,
  numPages,
  geoCorners,
  onPdfSelect,
  onPageChange,
  onSave,
  onDelete,
  onLocationSelect,
}: PdfSelectSidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const {
    results,
    loading: searchLoading,
    search,
    clear,
  } = useLocationSearch();

  const debouncedSearch = useDebouncedCallback((query: string) => {
    search(query);
  }, 300);

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    debouncedSearch(value);
  };

  const handleLocationClick = (result: (typeof results)[0]) => {
    onLocationSelect(result.boundingBox);
    setSearchQuery("");
    clear();
  };

  const labeledCount = Object.keys(labels).length;
  const isLabeled = selectedPdf && labels[selectedPdf.hash];

  return (
    <Stack gap="md">
      {/* Header */}
      <Group justify="space-between">
        <Title order={5}>Labeller</Title>
        <Badge variant="light">
          {labeledCount}/{pdfs.length}
        </Badge>
      </Group>

      <Divider label="Location" labelPosition="left" />

      {/* Location Search */}
      <TextInput
        placeholder="Search state, county..."
        leftSection={<IconSearch size={16} />}
        value={searchQuery}
        onChange={(e) => handleSearchChange(e.target.value)}
        rightSection={searchLoading && <Loader size="xs" />}
      />

      {/* Search Results */}
      {results.length > 0 && (
        <Paper withBorder p="xs" style={{ maxHeight: 150, overflow: "auto" }}>
          <Stack gap={4}>
            {results.map((result, i) => (
              <Button
                key={i}
                variant="subtle"
                size="compact-xs"
                justify="flex-start"
                onClick={() => handleLocationClick(result)}
                style={{ whiteSpace: "normal", height: "auto", padding: 4 }}
              >
                <Text size="xs" lineClamp={2}>
                  {result.displayName}
                </Text>
              </Button>
            ))}
          </Stack>
        </Paper>
      )}

      <Divider label="PDF" labelPosition="left" />

      {/* PDF Selector */}
      <Select
        placeholder="Select a PDF"
        data={pdfs.map((pdf) => ({
          value: pdf.hash,
          label: `${pdf.state}/${pdf.city}/${pdf.name}`,
        }))}
        value={selectedPdf?.hash || null}
        onChange={onPdfSelect}
        searchable
        clearable
        size="sm"
      />

      {/* Page selector for multi-page PDFs */}
      {selectedPdf && numPages > 1 && (
        <Select
          label="Page"
          value={String(pageNumber)}
          onChange={(v) => onPageChange(Number(v) || 1)}
          data={Array.from({ length: numPages }, (_, i) => ({
            value: String(i + 1),
            label: `Page ${i + 1} of ${numPages}`,
          }))}
          size="xs"
        />
      )}

      {selectedPdf && (
        <>
          <Divider />

          {/* Actions */}
          <Stack gap="xs">
            {isLabeled && (
              <Button
                size="sm"
                variant="outline"
                color="red"
                leftSection={<IconTrash size={16} />}
                onClick={onDelete}
              >
                Delete Label
              </Button>
            )}

            <Button
              size="sm"
              leftSection={<IconDeviceFloppy size={16} />}
              onClick={onSave}
              loading={saving}
            >
              Save Label
            </Button>
          </Stack>

          {isLabeled && (
            <Badge color="green" variant="light" size="sm">
              Already labeled
            </Badge>
          )}

          <Text size="xs" c="dimmed">
            Draw bounds on the map by clicking and dragging. Then drag to
            position and resize using corner handles. Click Save when done.
          </Text>

          {/* Geo Coordinates Display */}
          {geoCorners && (
            <>
              <Divider label="Coordinates" labelPosition="left" />
              <Paper withBorder p="xs" bg="dark.7">
                <Stack gap={4}>
                  <Group justify="space-between">
                    <Text size="xs" fw={500} c="dimmed">
                      GeoCorners (for embedding)
                    </Text>
                    <Button
                      size="compact-xs"
                      variant="subtle"
                      leftSection={<IconCopy size={12} />}
                      onClick={() => {
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
                      }}
                    >
                      Copy
                    </Button>
                  </Group>
                  <Text
                    size="xs"
                    ff="monospace"
                    style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}
                  >
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
        </>
      )}
    </Stack>
  );
}
