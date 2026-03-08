import type { NextApiRequest, NextApiResponse } from "next";
import * as labels from "@/server/labels";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    if (req.method === "GET") {
      const allLabels = await labels.getAllLabels();
      return res.status(200).json(allLabels);
    }

    if (req.method === "POST") {
      const { label } = req.body;
      await labels.saveLabel(label);
      return res.status(200).json({ success: true });
    }

    if (req.method === "DELETE") {
      const { pdfHash } = req.body;
      await labels.deleteLabel(pdfHash);
      return res.status(200).json({ success: true });
    }

    res.status(405).json({ error: "Method not allowed" });
  } catch (error) {
    console.error("Labels API error:", error);
    res.status(500).json({ error: "Database error" });
  }
}
