import type { NextApiRequest, NextApiResponse } from "next";
import fs from "fs";
import path from "path";
import { PdfFile } from "@/types/pdf";

/**
 * PDFs API - reads from DVC manifest instead of scanning filesystem.
 *
 * DVC stores a .dir file containing all file paths and their MD5 hashes.
 * This approach:
 * - Works in production (no filesystem access to data dir needed)
 * - Uses pre-computed hashes (fast, no heavy I/O)
 * - Stays in sync with DVC-tracked data
 */

interface DvcEntry {
  md5: string;
  relpath: string;
}

let cachedPdfs: PdfFile[] | null = null;

function loadPdfsFromManifest(): PdfFile[] {
  if (cachedPdfs) return cachedPdfs;

  const manifestPath = path.resolve(
    process.cwd(),
    process.env.DVC_MANIFEST ||
      "../.dvc/cache/files/md5/ac/a543f303438b3df1f6e174c47af627.dir"
  );

  const manifest: DvcEntry[] = JSON.parse(
    fs.readFileSync(manifestPath, "utf-8")
  );

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

export default function handler(
  _req: NextApiRequest,
  res: NextApiResponse<PdfFile[] | { error: string }>
) {
  try {
    const pdfs = loadPdfsFromManifest();
    res.status(200).json(pdfs);
  } catch (error) {
    console.error("Failed to load PDF manifest:", error);
    res.status(500).json({ error: "Failed to read PDF files" });
  }
}
