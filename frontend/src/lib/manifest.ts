import { hashToGcsPath } from "./gcs";
import { Storage } from "@google-cloud/storage";
import fs from "fs";
import path from "path";

/**
 * DVC manifest utilities - fetches manifest from GCS.
 *
 * The manifest contains all file paths and their MD5 hashes.
 * The manifest hash is read from dvc-manifest-hash.txt (git-tracked)
 * so it stays in sync with code deployments.
 */

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

/**
 * Read the manifest hash from the git-tracked file.
 */
function getManifestHash(): string {
  // Try env var first (allows override), then read from file
  if (process.env.DVC_MANIFEST_HASH) {
    return process.env.DVC_MANIFEST_HASH;
  }

  const hashFile = path.resolve(process.cwd(), "dvc-manifest-hash.txt");
  return fs.readFileSync(hashFile, "utf-8").trim();
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
