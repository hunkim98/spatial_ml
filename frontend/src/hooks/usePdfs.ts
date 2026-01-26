import { useState, useEffect } from "react";
import axios from "axios";
import { PdfFile } from "@/types/pdf";

interface UsePdfsReturn {
  pdfs: PdfFile[];
  loading: boolean;
  error: string | null;
}

export function usePdfs(): UsePdfsReturn {
  const [pdfs, setPdfs] = useState<PdfFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    axios
      .get<PdfFile[]>("/api/pdfs")
      .then((res) => setPdfs(res.data))
      .catch(() => setError("Failed to load PDFs"))
      .finally(() => setLoading(false));
  }, []);

  return { pdfs, loading, error };
}
