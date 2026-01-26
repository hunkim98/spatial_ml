"use client";

import { useState, useEffect, ComponentType } from "react";
import { Paper, Group, Button, Text, Loader, Center } from "@mantine/core";
import type { DocumentProps, PageProps } from "react-pdf";

interface PdfViewerProps {
  url: string;
  width?: number;
}

export function PdfViewer({ url, width = 380 }: PdfViewerProps) {
  const [numPages, setNumPages] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [PdfComponents, setPdfComponents] = useState<{
    Document: ComponentType<DocumentProps>;
    Page: ComponentType<PageProps>;
  } | null>(null);

  // Dynamically load react-pdf on client side only
  useEffect(() => {
    async function loadPdf() {
      const { Document, Page, pdfjs } = await import("react-pdf");
      pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
      // @ts-expect-error - CSS modules have no type definitions
      await import("react-pdf/dist/Page/AnnotationLayer.css");
      // @ts-expect-error - CSS modules have no type definitions
      await import("react-pdf/dist/Page/TextLayer.css");
      setPdfComponents({ Document, Page });
    }
    loadPdf();
  }, []);

  // Reset page when URL changes
  useEffect(() => {
    setPageNumber(1);
    setNumPages(0);
  }, [url]);

  if (!PdfComponents) {
    return (
      <Paper shadow="sm" p="xs">
        <Center p="xl">
          <Loader />
        </Center>
      </Paper>
    );
  }

  const { Document, Page } = PdfComponents;

  return (
    <Paper shadow="sm" p="xs" style={{ overflow: "auto" }}>
      <Document
        file={url}
        onLoadSuccess={({ numPages }: { numPages: number }) => {
          setNumPages(numPages);
        }}
        loading={
          <Center p="xl">
            <Loader />
          </Center>
        }
      >
        <Page
          pageNumber={pageNumber}
          width={width}
          renderTextLayer={false}
          renderAnnotationLayer={false}
        />
      </Document>

      {numPages > 1 && (
        <Group justify="center" mt="xs">
          <Button
            size="xs"
            disabled={pageNumber <= 1}
            onClick={() => setPageNumber((p) => p - 1)}
          >
            Prev
          </Button>
          <Text size="sm">
            {pageNumber} / {numPages}
          </Text>
          <Button
            size="xs"
            disabled={pageNumber >= numPages}
            onClick={() => setPageNumber((p) => p + 1)}
          >
            Next
          </Button>
        </Group>
      )}
    </Paper>
  );
}
