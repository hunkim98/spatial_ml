import type { NextApiRequest, NextApiResponse } from "next";
import fs from "fs";
import path from "path";
import { getFileStream } from "@/lib/gcs";

/**
 * PDF Image endpoint - returns PDF info for client-side rendering.
 *
 * Since server-side PDF rendering requires canvas (complex setup),
 * we return the PDF URL and let the client render it to canvas.
 *
 * Query params:
 * - page: Page number (default: 1)
 */

interface DvcEntry {
  md5: string;
  relpath: string;
}

let manifest: DvcEntry[] | null = null;

function getManifest(): DvcEntry[] {
  if (!manifest) {
    const manifestPath = path.resolve(
      process.cwd(),
      process.env.DVC_MANIFEST ||
        "../.dvc/cache/files/md5/ac/a543f303438b3df1f6e174c47af627.dir"
    );
    manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
  }
  return manifest!;
}

function findHashByPath(pdfPath: string): string | null {
  const fullPath = `maps/${pdfPath}`;
  const entry = getManifest().find((e) => e.relpath === fullPath);
  return entry?.md5 || null;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const { path: pathParts } = req.query;

  if (!pathParts || !Array.isArray(pathParts)) {
    return res.status(400).json({ error: "Invalid path" });
  }

  const pdfPath = pathParts.join("/");
  if (!pdfPath.endsWith(".pdf")) {
    return res.status(400).json({ error: "Invalid file type" });
  }

  const hash = findHashByPath(pdfPath);
  if (!hash) {
    return res.status(404).json({ error: "PDF not found" });
  }

  // Return PDF URL for client-side rendering
  // The client will use pdf.js to render to canvas
  res.status(200).json({
    pdfUrl: `/api/pdf/${pdfPath}`,
    hash,
    path: pdfPath,
  });
}
