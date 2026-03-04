import {
  Accordion,
  Badge,
  Group,
  ScrollArea,
  Stack,
  Text,
  Title,
  UnstyledButton,
} from "@mantine/core";
import { PdfFile } from "@/types/pdf";
import { GeoLabel, SkippedLabel } from "@/types/labels";
import { useMemo, useState } from "react";

interface PdfSelectSidebarProps {
  pdfs: PdfFile[];
  labels: Record<string, GeoLabel>;
  skippedLabels: Record<string, SkippedLabel>;
  onPdfSelect: (hash: string | null) => void;
}

function PdfSelectSidebar({
  pdfs,
  labels,
  skippedLabels,
  onPdfSelect,
}: PdfSelectSidebarProps) {
  const { unlabeled, skipped, labeled } = useMemo(() => {
    const unlabeled: PdfFile[] = [];
    const skipped: PdfFile[] = [];
    const labeled: PdfFile[] = [];

    for (const pdf of pdfs) {
      if (labels[pdf.hash]) {
        labeled.push(pdf);
      } else if (skippedLabels[pdf.hash]) {
        skipped.push(pdf);
      } else {
        unlabeled.push(pdf);
      }
    }

    return { unlabeled, skipped, labeled };
  }, [pdfs, labels, skippedLabels]);

  return (
    <Stack gap="md">
      <Group>
        <Title order={5}>Labeller</Title>
      </Group>

      <Accordion
        multiple
        defaultValue={["unlabeled", "skipped"]}
        variant="separated"
      >
        <Accordion.Item value="unlabeled">
          <Accordion.Control>
            <Group gap="xs">
              <Text size="sm" fw={500}>
                Unlabeled
              </Text>
              <Badge size="sm" color="blue" variant="light">
                {unlabeled.length}
              </Badge>
            </Group>
          </Accordion.Control>
          <Accordion.Panel>
            <PdfList pdfs={unlabeled} onSelect={onPdfSelect} />
          </Accordion.Panel>
        </Accordion.Item>

        <Accordion.Item value="skipped">
          <Accordion.Control>
            <Group gap="xs">
              <Text size="sm" fw={500}>
                Skipped
              </Text>
              <Badge size="sm" color="gray" variant="light">
                {skipped.length}
              </Badge>
            </Group>
          </Accordion.Control>
          <Accordion.Panel>
            <PdfList pdfs={skipped} onSelect={onPdfSelect} />
          </Accordion.Panel>
        </Accordion.Item>

        <Accordion.Item value="labeled">
          <Accordion.Control>
            <Group gap="xs">
              <Text size="sm" fw={500}>
                Labeled
              </Text>
              <Badge size="sm" color="green" variant="light">
                {labeled.length}
              </Badge>
            </Group>
          </Accordion.Control>
          <Accordion.Panel>
            <PdfList pdfs={labeled} onSelect={onPdfSelect} />
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>
    </Stack>
  );
}

function PdfList({
  pdfs,
  onSelect,
}: {
  pdfs: PdfFile[];
  onSelect: (hash: string) => void;
}) {
  if (pdfs.length === 0) {
    return (
      <Text size="xs" c="dimmed">
        None
      </Text>
    );
  }

  return (
    <ScrollArea.Autosize mah={300} type="auto">
      <Stack gap={4}>
        {pdfs.map((pdf) => (
          <PdfRow key={pdf.hash} pdf={pdf} onSelect={onSelect} />
        ))}
      </Stack>
    </ScrollArea.Autosize>
  );
}

function PdfRow({
  pdf,
  onSelect,
}: {
  pdf: PdfFile;
  onSelect: (hash: string) => void;
}) {
  const [hovered, setHovered] = useState(false);

  return (
    <UnstyledButton
      onClick={() => onSelect(pdf.hash)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      px="xs"
      py={4}
      style={{
        borderRadius: 4,
        backgroundColor: hovered ? "var(--mantine-color-gray-1)" : undefined,
      }}
    >
      <Text size="xs" truncate>
        {pdf.state}/{pdf.city}/{pdf.name}
      </Text>
    </UnstyledButton>
  );
}

export default PdfSelectSidebar;
