import { Stack, Title, Group, Button, Text, Loader } from "@mantine/core";
import { IconCrop } from "@tabler/icons-react";
import { useCallback, useEffect, useState } from "react";
import { ClipperEditorComponentHandle } from "../canvas/ClipperEditorComponent";
import { ClipperEvent } from "@/canvas/clipper/events";
import { ExportResult } from "@/canvas/clipper/controller/exportController";

interface ClipperSidebarProps {
  clipperRef: React.RefObject<ClipperEditorComponentHandle | null>;
  setClipResult: React.Dispatch<React.SetStateAction<ExportResult | null>>;
}

function ClipperSidebar({
  clipperRef,
  setClipResult,
}: ClipperSidebarProps) {
  const [pdfLoaded, setPdfLoaded] = useState(false);
  const [hasClipRect, setHasClipRect] = useState(false);

  const onPdfLoaded = useCallback(() => {
    setPdfLoaded(true);
  }, []);

  const onClipChanged = useCallback(() => {
    setHasClipRect(true);
  }, []);

  useEffect(() => {
    const handle = clipperRef.current;
    if (!handle) return;
    handle.addEventListener(ClipperEvent.PDF_LOADED, onPdfLoaded);
    handle.addEventListener(ClipperEvent.CLIP_CHANGED, onClipChanged);
    return () => {
      handle.removeEventListener(ClipperEvent.PDF_LOADED, onPdfLoaded);
      handle.removeEventListener(ClipperEvent.CLIP_CHANGED, onClipChanged);
    };
  }, [clipperRef, onPdfLoaded, onClipChanged]);

  const handleClip = () => {
    const result = clipperRef.current?.exportClippedImage();
    if (result) {
      setClipResult(result);
    }
  };

  return (
    <Stack gap="md">
      <Group>
        <Title order={5}>Clip Image</Title>
      </Group>

      {!pdfLoaded ? (
        <Group gap="xs">
          <Loader size="xs" />
          <Text size="sm" c="dimmed">
            Loading PDF...
          </Text>
        </Group>
      ) : (
        <Text size="sm" c="dimmed">
          Draw a rectangle on the PDF to select the map area, then click Clip.
        </Text>
      )}

      <Button
        leftSection={<IconCrop size={16} />}
        onClick={handleClip}
        disabled={!hasClipRect}
      >
        Clip
      </Button>
    </Stack>
  );
}

export default ClipperSidebar;
