import type { NextApiRequest, NextApiResponse } from "next";
import fs from "fs";
import path from "path";
import { getFileStream } from "@/lib/gcs";

/**
 * PDF serving endpoint - fetches from GCS using DVC cache structure.
 *
 * Flow:
 * 1. Receive path like "AL/huntsville/pdf/04-13.pdf"
 * 2. Look up MD5 hash from DVC manifest
 * 3. Fetch file from GCS at files/md5/{hash[0:2]}/{hash[2:]}
 * 4. Stream to client
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
    return res.status(404).json({ error: "PDF not found in manifest" });
  }

  try {
    const stream = getFileStream(hash);

    res.setHeader("Content-Type", "application/pdf");
    res.setHeader(
      "Content-Disposition",
      `inline; filename="${path.basename(pdfPath)}"`
    );
    res.setHeader("Cache-Control", "public, max-age=31536000, immutable");

    stream.pipe(res);

    stream.on("error", (err) => {
      console.error("GCS stream error:", err);
      if (!res.headersSent) {
        res.status(500).json({ error: "Failed to fetch PDF" });
      }
    });
  } catch (error) {
    console.error("PDF fetch error:", error);
    res.status(500).json({ error: "Failed to fetch PDF" });
  }
}
