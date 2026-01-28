import type { NextApiRequest, NextApiResponse } from "next";
import { findHashByPath } from "@/lib/manifest";

/**
 * PDF Image endpoint - returns PDF info for client-side rendering.
 *
 * Since server-side PDF rendering requires canvas (complex setup),
 * we return the PDF URL and let the client render it to canvas.
 *
 * Query params:
 * - page: Page number (default: 1)
 */

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

  const hash = await findHashByPath(pdfPath);
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
