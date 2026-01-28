import type { NextApiRequest, NextApiResponse } from "next";
import { PdfFile } from "@/types/pdf";
import { getManifest } from "@/lib/manifest";

/**
 * PDFs API - reads from DVC manifest fetched from GCS.
 *
 * DVC stores a .dir file containing all file paths and their MD5 hashes.
 * This approach:
 * - Works in production (fetches manifest from GCS)
 * - Uses pre-computed hashes (fast, no heavy I/O)
 * - Stays in sync with DVC-tracked data
 */

let cachedPdfs: PdfFile[] | null = null;

async function loadPdfsFromManifest(): Promise<PdfFile[]> {
  if (cachedPdfs) return cachedPdfs;

  const manifest = await getManifest();

  cachedPdfs = manifest
    .filter(
      (entry) =>
        entry.relpath.endsWith(".pdf") && entry.relpath.startsWith("maps/")
    )
    .map((entry) => {
      // relpath format: "maps/STATE/CITY/pdf/filename.pdf"
      const parts = entry.relpath.split("/");
      return {
        hash: entry.md5,
        path: entry.relpath.replace(/^maps\//, ""), // Remove "maps/" prefix
        name: parts[parts.length - 1],
        state: parts[1] || "",
        city: parts[2] || "",
      };
    });

  return cachedPdfs;
}

export default async function handler(
  _req: NextApiRequest,
  res: NextApiResponse<PdfFile[] | { error: string }>
) {
  try {
    const pdfs = await loadPdfsFromManifest();
    res.status(200).json(pdfs);
  } catch (error) {
    console.error("Failed to load PDF manifest:", error);
    res.status(500).json({ error: "Failed to read PDF files" });
  }
}
