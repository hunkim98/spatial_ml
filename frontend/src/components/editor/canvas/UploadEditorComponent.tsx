import { forwardRef, useCallback, useImperativeHandle, useRef } from "react";
import { Stack, Text, Title, Button, Paper } from "@mantine/core";
import { IconUpload, IconPhoto } from "@tabler/icons-react";

export interface UploadEditorComponentHandle {
  /** Trigger file picker programmatically */
  openFilePicker: () => void;
}

interface UploadEditorComponentProps {
  onImageSelect: (
    file: File,
    url: string,
    width: number,
    height: number
  ) => void;
}

export const UploadEditorComponent = forwardRef<
  UploadEditorComponentHandle,
  UploadEditorComponentProps
>(function UploadEditorComponent({ onImageSelect }, ref) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      const url = URL.createObjectURL(file);
      const img = new window.Image();
      img.onload = () =>
        onImageSelect(file, url, img.naturalWidth, img.naturalHeight);
      img.src = url;
    },
    [onImageSelect]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith("image/")) handleFile(file);
    },
    [handleFile]
  );

  useImperativeHandle(
    ref,
    () => ({
      openFilePicker: () => inputRef.current?.click(),
    }),
    []
  );

  return (
    <div
      className="w-full h-full flex items-center justify-center"
      style={{ background: "#f0f0f0" }}
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
    >
      <Paper
        p="xl"
        withBorder
        style={{
          borderStyle: "dashed",
          borderWidth: 2,
          cursor: "pointer",
          maxWidth: 500,
          width: "100%",
        }}
        onClick={() => inputRef.current?.click()}
      >
        <Stack align="center" gap="md">
          <IconPhoto size={48} color="gray" />
          <Title order={4}>Upload a Zoning Map</Title>
          <Text size="sm" c="dimmed" ta="center">
            Drag and drop an image here, or click to browse.
            <br />
            Supports PNG, JPG, TIFF.
          </Text>
          <Button leftSection={<IconUpload size={16} />} variant="light">
            Choose File
          </Button>
        </Stack>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          onChange={handleChange}
          style={{ display: "none" }}
        />
      </Paper>
    </div>
  );
});
