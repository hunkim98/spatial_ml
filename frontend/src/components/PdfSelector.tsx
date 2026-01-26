import { Select } from "@mantine/core";
import { PdfFile } from "@/types/pdf";

interface PdfSelectorProps {
  pdfs: PdfFile[];
  value: string | null;
  onChange: (pdf: PdfFile | null) => void;
  label?: string;
  placeholder?: string;
}

export function PdfSelector({
  pdfs,
  value,
  onChange,
  label = "Select PDF",
  placeholder = "Choose a PDF",
}: PdfSelectorProps) {
  return (
    <Select
      label={label}
      placeholder={placeholder}
      data={pdfs.map((pdf) => ({
        value: pdf.hash,
        label: `${pdf.state}/${pdf.city}/${pdf.name}`,
      }))}
      value={value}
      onChange={(hash) => {
        const pdf = pdfs.find((p) => p.hash === hash) || null;
        onChange(pdf);
      }}
      searchable
      clearable
    />
  );
}
