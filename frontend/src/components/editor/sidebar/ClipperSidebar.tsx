import { Stack, Title, Group, Button, Text, Loader } from "@mantine/core";
import { IconArrowLeft, IconCrop, IconPlayerSkipForward } from "@tabler/icons-react";
import { useCallback, useEffect, useState } from "react";
import { ClipperEditorComponentHandle } from "../canvas/ClipperEditorComponent";
import { ClipperEvent } from "@/canvas/clipper/events";
import { ExportResult } from "@/canvas/clipper/controller/exportController";
import { PdfFile } from "@/types/pdf";

interface ClipperSidebarProps {
  selectedPdf: PdfFile | null;
  clipperRef: React.RefObject<ClipperEditorComponentHandle | null>;
  setClipResult: React.Dispatch<React.SetStateAction<ExportResult | null>>;
  onSkip: () => void;
  onBack: () => void;
}

function ClipperSidebar({
  selectedPdf,
  clipperRef,
  setClipResult,
  onSkip,
  onBack,
}: ClipperSidebarProps) {
  const [isPdfLoaded, setIsPdfLoaded] = useState(false);
  const [hasClipRect, setHasClipRect] = useState(false);

  const onPdfLoaded = useCallback(() => {
    setIsPdfLoaded(true);
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
    try {
      const result = clipperRef.current?.exportClippedImage();
      if (result) {
        setClipResult(result);
      } else {
        throw new Error("No result from exportClippedImage");
      }
    } catch (error) {
      console.error("Error exporting clipped image", error);
    }
  };

  return (
    <Stack gap="md">
      <Group>
        <Button
          variant="subtle"
          size="compact-sm"
          onClick={onBack}
          p={0}
        >
          <IconArrowLeft size={16} />
        </Button>
        <Title order={5}>Clip Image</Title>
      </Group>

      {selectedPdf && (
        <Text size="xs" c="dimmed" truncate>
          {selectedPdf.path.split("/").slice(0, -1).join("/")}
        </Text>
      )}

      {!isPdfLoaded ? (
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

      <Group>
        <Button
          leftSection={<IconCrop size={16} />}
          onClick={handleClip}
          disabled={!hasClipRect}
        >
          Clip
        </Button>
        <Button
          leftSection={<IconPlayerSkipForward size={16} />}
          onClick={onSkip}
          disabled={!isPdfLoaded}
          variant="light"
          color="gray"
        >
          Skip
        </Button>
      </Group>
    </Stack>
  );
}

export default ClipperSidebar;
