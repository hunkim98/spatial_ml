import { Storage } from "@google-cloud/storage";
import path from "path";

/**
 * GCS utility for accessing DVC-stored files.
 *
 * DVC stores files in GCS using MD5 hash-based paths:
 * gs://bucket/files/md5/{first2chars}/{remaining}
 *
 * Example: hash "abc123def456" -> "files/md5/ab/c123def456"
 */

let storage: Storage | null = null;

function getStorage(): Storage {
  if (!storage) {
    const credPath = path.resolve(
      process.cwd(),
      process.env.GOOGLE_APPLICATION_CREDENTIALS ||
        "../secrets/teamspatially-storage-accessor-keys.json"
    );
    storage = new Storage({ keyFilename: credPath });
  }
  return storage;
}

/**
 * Convert MD5 hash to DVC cache path.
 */
export function hashToGcsPath(hash: string): string {
  return `files/md5/${hash.slice(0, 2)}/${hash.slice(2)}`;
}

/**
 * Get a readable stream for a file from GCS by its MD5 hash.
 */
export function getFileStream(hash: string) {
  const bucket = process.env.GCS_BUCKET || "zoning_data";
  const gcsPath = hashToGcsPath(hash);
  return getStorage().bucket(bucket).file(gcsPath).createReadStream();
}

/**
 * Get file metadata from GCS.
 */
export async function getFileMetadata(hash: string) {
  const bucket = process.env.GCS_BUCKET || "zoning_data";
  const gcsPath = hashToGcsPath(hash);
  const [metadata] = await getStorage().bucket(bucket).file(gcsPath).getMetadata();
  return metadata;
}
