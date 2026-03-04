import type { NextApiRequest, NextApiResponse } from "next";
import * as skippedLabels from "@/server/skippedLabels";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    if (req.method === "GET") {
      const all = await skippedLabels.getAllSkippedLabels();
      return res.status(200).json(all);
    }

    if (req.method === "POST") {
      const { pdfHash, pdfPath } = req.body;
      await skippedLabels.skipLabel(pdfHash, pdfPath);
      return res.status(200).json({ success: true });
    }

    if (req.method === "DELETE") {
      const { pdfHash } = req.body;
      await skippedLabels.unskipLabel(pdfHash);
      return res.status(200).json({ success: true });
    }

    res.status(405).json({ error: "Method not allowed" });
  } catch (error) {
    console.error("Skipped labels API error:", error);
    res.status(500).json({ error: "Database error" });
  }
}
