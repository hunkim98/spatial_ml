import { getSupabaseClient } from "@/server/supabase";
import { GeoLabel } from "@/types/labels";

// ========== Row Mapping ==========

function rowToLabel(row: any): GeoLabel {
  return {
    pdfHash: row.pdf_hash,
    pdfPath: row.pdf_path,
    corners: {
      topLeft: { lng: row.top_left_lng, lat: row.top_left_lat },
      topRight: { lng: row.top_right_lng, lat: row.top_right_lat },
      bottomRight: { lng: row.bottom_right_lng, lat: row.bottom_right_lat },
      bottomLeft: { lng: row.bottom_left_lng, lat: row.bottom_left_lat },
    },
    clipRect: {
      offsetX: row.clip_offset_x,
      offsetY: row.clip_offset_y,
      width: row.clip_width,
      height: row.clip_height,
    },
    pageNumber: row.page_number,
    clippedImageUrl: row.clipped_image_url,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

// ========== Label CRUD ==========

export async function getAllLabels(): Promise<Record<string, GeoLabel>> {
  const client = getSupabaseClient();
  const { data, error } = await client
    .from("labels")
    .select("*")
    .order("updated_at", { ascending: false });

  if (error) throw error;

  const labels: Record<string, GeoLabel> = {};
  for (const row of data) {
    labels[row.pdf_hash] = rowToLabel(row);
  }
  return labels;
}

export async function getLabelByHash(
  pdfHash: string
): Promise<GeoLabel | null> {
  const client = getSupabaseClient();
  const { data, error } = await client
    .from("labels")
    .select("*")
    .eq("pdf_hash", pdfHash)
    .single();

  if (error) {
    if (error.code === "PGRST116") return null;
    throw error;
  }
  return rowToLabel(data);
}

export async function saveLabel(label: GeoLabel): Promise<void> {
  const client = getSupabaseClient();
  const { error } = await client.from("labels").upsert(
    {
      pdf_hash: label.pdfHash,
      pdf_path: label.pdfPath,
      top_left_lng: label.corners.topLeft.lng,
      top_left_lat: label.corners.topLeft.lat,
      top_right_lng: label.corners.topRight.lng,
      top_right_lat: label.corners.topRight.lat,
      bottom_right_lng: label.corners.bottomRight.lng,
      bottom_right_lat: label.corners.bottomRight.lat,
      bottom_left_lng: label.corners.bottomLeft.lng,
      bottom_left_lat: label.corners.bottomLeft.lat,
      clip_offset_x: label.clipRect.offsetX,
      clip_offset_y: label.clipRect.offsetY,
      clip_width: label.clipRect.width,
      clip_height: label.clipRect.height,
      page_number: label.pageNumber,
      clipped_image_url: label.clippedImageUrl,
      updated_at: new Date().toISOString(),
    },
    { onConflict: "pdf_hash" }
  );

  if (error) throw error;
}

export async function deleteLabel(pdfHash: string): Promise<void> {
  const client = getSupabaseClient();
  const { error } = await client
    .from("labels")
    .delete()
    .eq("pdf_hash", pdfHash);

  if (error) throw error;
}

