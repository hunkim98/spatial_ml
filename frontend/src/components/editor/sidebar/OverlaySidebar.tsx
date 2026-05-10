import {
  Box,
  Button,
  Divider,
  Group,
  Image as MantineImage,
  Loader,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDebouncedCallback } from "@mantine/hooks";
import { IconArrowLeft, IconSearch } from "@tabler/icons-react";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { OverlayEditorComponentHandle } from "../canvas/OverlayEditorComponent";
import { MapEditorComponentHandle } from "../canvas/MapEditorComponent";
import { GeoCorners } from "@/canvas/overlay/types";
import { useLocationSearch } from "@/hooks/useLocationSearch";

interface OverlaySidebarProps {
  clippedImageBuffer: HTMLCanvasElement;
  overlayRef: React.RefObject<OverlayEditorComponentHandle | null>;
  mapRef: React.RefObject<MapEditorComponentHandle | null>;
  imageGeoCorners: GeoCorners | null;
  setImageGeoCorners: React.Dispatch<React.SetStateAction<GeoCorners | null>>;
  onSaveLabel: () => void;
  isSaving: boolean;
  onBackToSelectPdf: () => void;
  onBackToClipper: () => void;
}

function OverlaySidebar({
  clippedImageBuffer,
  overlayRef,
  mapRef,
  imageGeoCorners,
  setImageGeoCorners,
  onSaveLabel,
  isSaving,
  onBackToSelectPdf,
  onBackToClipper,
}: OverlaySidebarProps) {
  const [isHoveringButton, setIsHoveringButton] = useState(false);
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

  const handleClickClippedImage = useCallback(() => {
    onBackToClipper();
  }, [onBackToClipper]);

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    debouncedSearch(value);
  };

  const handleLocationClick = (result: (typeof results)[0]) => {
    const [south, north, west, east] = result.boundingBox;
    mapRef.current?.getMapRef()?.fitBounds(
      [
        [west, south],
        [east, north],
      ],
      { padding: 40 }
    );
    setSearchQuery("");
    clear();
  };

  const previewUrl = useMemo(
    () => clippedImageBuffer?.toDataURL("image/png") ?? null,
    [clippedImageBuffer]
  );

  // Toggle canvas preview opacity on hover
  useEffect(() => {
    if (!overlayRef.current) return;
    const controllers = overlayRef.current?.getControllers();
    if (isHoveringButton) {
      controllers?.imagePropertyController.execute({
        opacity: 0.5,
        visible: true,
      });
    } else {
      controllers?.imagePropertyController.execute({ visible: false });
    }
  }, [overlayRef, isHoveringButton]);

  return (
    <Stack gap="md">
      <Group>
        <Button
          variant="subtle"
          size="compact-sm"
          onClick={onBackToSelectPdf}
          p={0}
        >
          <IconArrowLeft size={16} />
        </Button>
        <Title order={5}>Georeference</Title>
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

      {previewUrl && (
        <>
          <Box
            bg="black"
            style={{ borderRadius: 4, cursor: "pointer" }}
            onClick={handleClickClippedImage}
          >
            <MantineImage
              src={previewUrl}
              alt="Clipped Image"
              fit="contain"
              h={200}
            />
          </Box>
          <Button
            onMouseEnter={() => setIsHoveringButton(true)}
            onMouseLeave={() => setIsHoveringButton(false)}
            disabled={imageGeoCorners !== null}
            onClick={() => {
              const geoCorners = overlayRef.current?.getCorners();
              if (!geoCorners || !previewUrl) return;
              // Hide canvas preview, add to MapLibre
              const controllers = overlayRef.current?.getControllers();
              controllers?.imagePropertyController.execute({ visible: false });
              mapRef.current?.addImageLayer(previewUrl, geoCorners, 0.7);
              setImageGeoCorners(geoCorners);
            }}
          >
            {imageGeoCorners ? "Image Inserted" : "Insert Image"}
          </Button>
          {imageGeoCorners && (
            <Button
              variant="outline"
              color="red"
              onClick={() => {
                mapRef.current?.removeImageLayer();
                setImageGeoCorners(null);
              }}
            >
              Remove Image
            </Button>
          )}
        </>
      )}
      {imageGeoCorners && (
        <Button
          onClick={onSaveLabel}
          loading={isSaving}
        >
          Generate Polygons
        </Button>
      )}
    </Stack>
  );
}

export default OverlaySidebar;
