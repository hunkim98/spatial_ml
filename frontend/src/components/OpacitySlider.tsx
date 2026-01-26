"use client";

import { Slider, Text, Group, Paper } from "@mantine/core";
import { useEditorContext } from "@/canvas/context";

export function OpacitySlider() {
  const { opacity, setOpacity } = useEditorContext();

  return (
    <Paper
      shadow="md"
      p="sm"
      radius="md"
      style={{
        position: "absolute",
        bottom: 80,
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 30,
        minWidth: 200,
        background: "rgba(255, 255, 255, 0.95)",
      }}
    >
      <Group gap="xs" mb={4}>
        <Text size="xs" fw={500}>
          Opacity
        </Text>
        <Text size="xs" c="dimmed">
          {Math.round(opacity * 100)}%
        </Text>
      </Group>
      <Slider
        value={opacity}
        onChange={setOpacity}
        min={0.1}
        max={1}
        step={0.05}
        size="sm"
      />
    </Paper>
  );
}
