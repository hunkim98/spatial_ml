import { Stack, Title, Select, Group } from "@mantine/core";
import { PdfFile } from "@/types/pdf";

interface PdfSelectSidebarProps {
  pdfs: PdfFile[];
  onPdfSelect: (hash: string | null) => void;
}

function PdfSelectSidebar({ pdfs, onPdfSelect }: PdfSelectSidebarProps) {
  return (
    <Stack gap="md">
      <Group>
        <Title order={5}>Studio</Title>
      </Group>

      <Select
        placeholder="Select a PDF"
        data={pdfs.map((pdf) => ({
          value: pdf.hash,
          label: `${pdf.state}/${pdf.city}/${pdf.name}`,
        }))}
        onChange={onPdfSelect}
        searchable
        clearable
        size="sm"
      />
    </Stack>
  );
}

export default PdfSelectSidebar;
