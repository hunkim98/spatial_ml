import type { NextApiRequest, NextApiResponse } from "next";
import { getManifest } from "@/lib/manifest";
import { getFileStream } from "@/lib/gcs";

/**
 * GeoJSON serving endpoint - fetches from GCS using DVC cache structure.
 *
 * Path format: /api/geojson/AL/anniston/Anniston_Zoning.json
 */

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const { path: pathParts } = req.query;

  if (!pathParts || !Array.isArray(pathParts)) {
    return res.status(400).json({ error: "Invalid path" });
  }

  const filePath = pathParts.join("/");

  if (!filePath.endsWith(".json")) {
    return res.status(400).json({ error: "Invalid file type" });
  }

  // Look up in manifest - geojson files are under maps/{state}/{city}/geojson/
  const manifest = await getManifest();
  const fullPath = `maps/${filePath.replace("/geojson/", "/geojson/")}`;

  // Try different path patterns
  const possiblePaths = [
    `maps/${filePath}`,
    `maps/${pathParts[0]}/${pathParts[1]}/geojson/${pathParts.slice(2).join("/")}`,
  ];

  let hash: string | null = null;
  for (const p of possiblePaths) {
    const entry = manifest.find((e) => e.relpath === p);
    if (entry) {
      hash = entry.md5;
      break;
    }
  }

  if (!hash) {
    return res.status(404).json({ error: "GeoJSON not found in manifest" });
  }

  try {
    const stream = getFileStream(hash);

    res.setHeader("Content-Type", "application/json");
    res.setHeader("Cache-Control", "public, max-age=31536000, immutable");

    stream.pipe(res);

    stream.on("error", (err) => {
      console.error("GCS stream error:", err);
      if (!res.headersSent) {
        res.status(500).json({ error: "Failed to fetch GeoJSON" });
      }
    });
  } catch (error) {
    console.error("GeoJSON fetch error:", error);
    res.status(500).json({ error: "Failed to fetch GeoJSON" });
  }
}
