import {
  ActionIcon,
  Box,
  Button,
  ColorSwatch,
  Divider,
  Group,
  Image as MantineImage,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { IconArrowLeft, IconTrash } from "@tabler/icons-react";
import { PatternCircle } from "@/canvas/pattern_selector/types";
import { PatternSelectorEditorComponentHandle } from "../canvas/PatternSelectorEditorComponent";
import { useCallback, useMemo } from "react";

interface PatternSelectorSidebarProps {
  patterns: PatternCircle[];
  patternSelectorRef: React.RefObject<PatternSelectorEditorComponentHandle | null>;
  onNext: () => void;
  onBack: () => void;
}

export default function PatternSelectorSidebar({
  patterns,
  patternSelectorRef,
  onNext,
  onBack,
}: PatternSelectorSidebarProps) {
  const handleRemove = useCallback(
    (id: string) => {
      patternSelectorRef.current?.removePattern(id);
    },
    [patternSelectorRef]
  );

  const handleRename = useCallback(
    (id: string, name: string) => {
      patternSelectorRef.current?.renamePattern(id, name);
    },
    [patternSelectorRef]
  );

  // Generate preview URLs for each pattern
  const previews = useMemo(() => {
    const map: Record<string, string> = {};
    for (const pattern of patterns) {
      const result = patternSelectorRef.current?.exportPatternCrop(pattern.id);
      if (result) {
        map[pattern.id] = result.buffer.toDataURL("image/png");
      }
    }
    return map;
  }, [patterns, patternSelectorRef]);

  return (
    <Stack gap="md">
      <Group>
        <Button variant="subtle" size="compact-sm" onClick={onBack} p={0}>
          <IconArrowLeft size={16} />
        </Button>
        <Title order={5}>Select Patterns</Title>
      </Group>

      <Text size="sm" c="dimmed">
        Click on the map to select zone patterns. Drag the edge to resize, drag
        the body to move.
      </Text>

      <Text size="xs" c="dimmed">
        Hold <b>Space</b> + drag to pan. Scroll to zoom.
      </Text>

      <Divider
        label={`Patterns (${patterns.length})`}
        labelPosition="left"
      />

      {patterns.length === 0 && (
        <Text size="sm" c="dimmed" ta="center" py="xl">
          Click on a zone in the image to add a pattern.
        </Text>
      )}

      <Stack gap="xs">
        {patterns.map((pattern) => (
          <Paper key={pattern.id} withBorder p="xs">
            <Group gap="xs" wrap="nowrap" mb={4}>
              {previews[pattern.id] ? (
                <MantineImage
                  src={previews[pattern.id]}
                  alt={pattern.name}
                  w={36}
                  h={36}
                  fit="cover"
                  radius="sm"
                />
              ) : (
                <ColorSwatch
                  color={`rgb(${pattern.color[0]}, ${pattern.color[1]}, ${pattern.color[2]})`}
                  size={36}
                />
              )}
              <Box style={{ flex: 1 }}>
                <TextInput
                  size="xs"
                  placeholder="Zone name..."
                  value={pattern.name}
                  onChange={(e) =>
                    handleRename(pattern.id, e.currentTarget.value)
                  }
                />
              </Box>
              <ActionIcon
                variant="subtle"
                color="red"
                size="sm"
                onClick={() => handleRemove(pattern.id)}
              >
                <IconTrash size={14} />
              </ActionIcon>
            </Group>
          </Paper>
        ))}
      </Stack>

      {patterns.length > 0 && (
        <Button onClick={onNext} fullWidth>
          Next
        </Button>
      )}
    </Stack>
  );
}
