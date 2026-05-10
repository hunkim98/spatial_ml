import { Stack, Title, Text, Button, Card, Group } from "@mantine/core";
import { IconUpload, IconPhoto } from "@tabler/icons-react";
import { UploadEditorComponentHandle } from "../canvas/UploadEditorComponent";

interface UploadSidebarProps {
  uploadRef: React.RefObject<UploadEditorComponentHandle | null>;
  mapImageFile: File | null;
  mapImageDimensions: { width: number; height: number } | null;
}

function UploadSidebar({
  uploadRef,
  mapImageFile,
  mapImageDimensions,
}: UploadSidebarProps) {
  return (
    <Stack gap="md">
      <Title order={5}>Zone Segmentation</Title>

      <Text size="sm" c="dimmed">
        Upload a zoning map image to begin. The image will be cropped,
        georeferenced, and segmented into zone polygons.
      </Text>

      {mapImageFile && mapImageDimensions ? (
        <Card padding="sm" withBorder>
          <Group gap="xs" mb="xs">
            <IconPhoto size={16} />
            <Text size="sm" fw={500} truncate style={{ maxWidth: 200 }}>
              {mapImageFile.name}
            </Text>
          </Group>
          <Text size="xs" c="dimmed">
            {mapImageDimensions.width} x {mapImageDimensions.height} px
          </Text>
          <Text size="xs" c="dimmed">
            {(mapImageFile.size / 1024 / 1024).toFixed(1)} MB
          </Text>
        </Card>
      ) : (
        <Button
          leftSection={<IconUpload size={16} />}
          variant="light"
          onClick={() => uploadRef.current?.openFilePicker()}
        >
          Choose File
        </Button>
      )}
    </Stack>
  );
}

export default UploadSidebar;
