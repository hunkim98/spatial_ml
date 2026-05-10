import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
});

export interface SegmentRequest {
  image: File;
  patterns: Array<{ name: string; crop: Blob }>;
  extent: { xmin: number; ymin: number; xmax: number; ymax: number };
  threshold?: number;
}

export interface HealthResponse {
  status: string;
  device: string;
  model: string;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/api/health");
  return data;
}

export async function postSegmentation(
  params: SegmentRequest
): Promise<GeoJSON.FeatureCollection> {
  const formData = new FormData();
  formData.append("image", params.image);
  params.patterns.forEach((p) =>
    formData.append("patterns", p.crop, `${p.name}.png`)
  );
  formData.append(
    "pattern_names",
    JSON.stringify(params.patterns.map((p) => p.name))
  );
  formData.append("extent", JSON.stringify(params.extent));
  if (params.threshold !== undefined) {
    formData.append("threshold", String(params.threshold));
  }

  const { data } = await api.post<GeoJSON.FeatureCollection>(
    "/api/segment",
    formData
  );
  return data;
}
