import {
  Box,
  Group,
  Stack,
  Title,
  Image as MantineImage,
  Button,
} from "@mantine/core";
import React, { useEffect, useMemo, useState } from "react";
import { OverlayEditorComponentHandle } from "../canvas/OverlayEditorComponent";
import { MapEditorComponentHandle } from "../canvas/MapEditorComponent";
import { GeoCorners } from "@/canvas/overlay/types";

interface OverlaySidebarProps {
  clippedImageBuffer: HTMLCanvasElement | null;
  setClippedImageBuffer: React.Dispatch<
    React.SetStateAction<HTMLCanvasElement | null>
  >;
  overlayRef: React.RefObject<OverlayEditorComponentHandle | null>;
  mapRef: React.RefObject<MapEditorComponentHandle | null>;
  imageGeoCorners: GeoCorners | null;
  setImageGeoCorners: React.Dispatch<React.SetStateAction<GeoCorners | null>>;
}

function OverlaySidebar({
  clippedImageBuffer,
  setClippedImageBuffer,
  overlayRef,
  mapRef,
  imageGeoCorners,
  setImageGeoCorners,
}: OverlaySidebarProps) {
  const [isHoveringButton, setIsHoveringButton] = useState(false);

  const previewUrl = useMemo(
    () => clippedImageBuffer?.toDataURL("image/png") ?? null,
    [clippedImageBuffer]
  );

  // Toggle canvas preview opacity on hover
  useEffect(() => {
    if (!overlayRef.current) return;
    const controllers = overlayRef.current?.getControllers();
    if (isHoveringButton) {
      controllers?.imagePropertyController.execute({ opacity: 0.5 });
      // overlayRef.current?.preloadMapImage();
    } else {
      controllers?.imagePropertyController.execute({ opacity: 0 });
    }
  }, [overlayRef, isHoveringButton]);

  return (
    <Stack gap="md">
      <Group>
        <Title order={5}>Overlay</Title>
      </Group>
      {previewUrl && (
        <>
          <Box bg="black" style={{ borderRadius: 4 }}>
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
              controllers?.imagePropertyController.execute({ opacity: 0 });
              mapRef.current?.addImageLayer(previewUrl, geoCorners, 0.7);
              setImageGeoCorners(geoCorners);
            }}
          >
            {imageGeoCorners ? "Image Inserted" : "Insert Image"}
          </Button>
        </>
      )}
    </Stack>
  );
}

export default OverlaySidebar;
