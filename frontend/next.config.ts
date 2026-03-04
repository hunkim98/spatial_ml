import type { NextConfig } from "next";
import fs from "fs";
import path from "path";

function getDvcManifestHash(): string {
  const dvcFile = path.resolve(process.cwd(), "..", "data.dvc");
  if (!fs.existsSync(dvcFile)) {
    // Fallback to hash file if data.dvc not accessible (e.g. standalone deploy)
    const hashFile = path.resolve(process.cwd(), "dvc-manifest-hash.txt");
    if (fs.existsSync(hashFile)) {
      return fs.readFileSync(hashFile, "utf-8").trim();
    }
    throw new Error("Cannot find data.dvc or dvc-manifest-hash.txt");
  }
  const content = fs.readFileSync(dvcFile, "utf-8");
  const match = content.match(/md5:\s*([a-f0-9]+)\.dir/);
  if (!match) throw new Error("Could not parse manifest hash from data.dvc");
  return match[1];
}

const nextConfig: NextConfig = {
  reactStrictMode: true,
  env: {
    DVC_MANIFEST_HASH: getDvcManifestHash(),
  },
};

export default nextConfig;
