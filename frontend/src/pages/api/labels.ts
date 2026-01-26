import type { NextApiRequest, NextApiResponse } from "next";
import db, { GeoLabel } from "@/lib/db";

/**
 * Labels API - CRUD operations for PDF georeferencing labels.
 *
 * Labels are keyed by pdf_hash (MD5 of file content) so they survive
 * file moves and work across different DVC checkouts.
 *
 * GET    - Returns all labels as { [hash]: GeoLabel }
 * POST   - Save/update a label (upsert by hash)
 * DELETE - Delete a label by hash
 */
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    if (req.method === "GET") {
      const labels = await db.getAllLabels();
      return res.status(200).json(labels);
    }

    if (req.method === "POST") {
      const label: GeoLabel = req.body;
      await db.saveLabel(label);
      return res.status(200).json({ success: true });
    }

    if (req.method === "DELETE") {
      const { pdfHash } = req.body;
      await db.deleteLabel(pdfHash);
      return res.status(200).json({ success: true });
    }

    res.status(405).json({ error: "Method not allowed" });
  } catch (error) {
    console.error("Labels API error:", error);
    res.status(500).json({ error: "Database error" });
  }
}
