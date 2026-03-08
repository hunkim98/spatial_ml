import { hashToGcsPath } from "./gcs";
import { Storage } from "@google-cloud/storage";

export interface DvcEntry {
  md5: string;
  relpath: string;
}

let cachedManifest: DvcEntry[] | null = null;
let storage: Storage | null = null;

function getStorage(): Storage {
  if (!storage) {
    if (process.env.GOOGLE_SERVICE_ACCOUNT_KEY) {
      const credentials = JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_KEY);
      storage = new Storage({ credentials });
    } else {
      // Fallback for local dev with default credentials
      storage = new Storage();
    }
  }
  return storage;
}

function getManifestHash(): string {
  // Injected at build time by next.config.ts from data.dvc
  if (!process.env.DVC_MANIFEST_HASH) {
    throw new Error("DVC_MANIFEST_HASH not set — check next.config.ts");
  }
  return process.env.DVC_MANIFEST_HASH;
}

/**
 * Get the DVC manifest, fetching from GCS if needed.
 */
export async function getManifest(): Promise<DvcEntry[]> {
  if (cachedManifest) return cachedManifest;

  const manifestHash = getManifestHash();
  const bucket = process.env.GCS_BUCKET || "zoning_data";
  // DVC .dir files (manifests) are stored with .dir extension in GCS
  const gcsPath = hashToGcsPath(manifestHash) + ".dir";

  const [content] = await getStorage()
    .bucket(bucket)
    .file(gcsPath)
    .download();

  cachedManifest = JSON.parse(content.toString("utf-8"));
  return cachedManifest!;
}

/**
 * Find the MD5 hash for a given file path.
 */
export async function findHashByPath(pdfPath: string): Promise<string | null> {
  const fullPath = `maps/${pdfPath}`;
  const manifest = await getManifest();
  const entry = manifest.find((e) => e.relpath === fullPath);
  return entry?.md5 || null;
}
