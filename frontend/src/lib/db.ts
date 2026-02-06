import { createClient, SupabaseClient } from "@supabase/supabase-js";

/**
 * GeoLabel represents the georeferencing data for a PDF map.
 *
 * We use a hybrid identification approach:
 * - pdfHash: MD5 hash of the file content (primary identifier)
 * - pdfPath: Human-readable path (for display, updated if file moves)
 *
 * This ensures labels survive file reorganization and work across DVC checkouts.
 */
export interface GeoLabel {
  pdfHash: string;      // MD5 hash - the stable unique identifier
  pdfPath: string;      // Current file path - may change if file moves
  corners: {
    topLeft: { lng: number; lat: number };
    topRight: { lng: number; lat: number };
    bottomRight: { lng: number; lat: number };
    bottomLeft: { lng: number; lat: number };
  };
  createdAt?: string;
  updatedAt?: string;
}

class SupabaseDB {
  private client: SupabaseClient;

  constructor() {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    if (!url || !key) {
      throw new Error(
        "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY"
      );
    }
    this.client = createClient(url, key);
  }

  /**
   * Get all labels from the database.
   * Returns a map keyed by pdf_hash for easy lookup.
   */
  async getAllLabels(): Promise<Record<string, GeoLabel>> {
    const { data, error } = await this.client
      .from("labels")
      .select("*")
      .order("updated_at", { ascending: false });

    if (error) throw error;

    const labels: Record<string, GeoLabel> = {};
    for (const row of data) {
      labels[row.pdf_hash] = this.rowToLabel(row);
    }
    return labels;
  }

  /**
   * Get a label by its PDF hash.
   */
  async getLabelByHash(pdfHash: string): Promise<GeoLabel | null> {
    const { data, error } = await this.client
      .from("labels")
      .select("*")
      .eq("pdf_hash", pdfHash)
      .single();

    if (error) {
      if (error.code === "PGRST116") return null; // no rows
      throw error;
    }
    return this.rowToLabel(data);
  }

  /**
   * Save or update a label.
   * Uses pdf_hash as the unique key (ON CONFLICT).
   * If the same hash exists with a different path, the path is updated.
   */
  async saveLabel(label: GeoLabel): Promise<void> {
    const { error } = await this.client.from("labels").upsert(
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
        updated_at: new Date().toISOString(),
      },
      { onConflict: "pdf_hash" }
    );

    if (error) throw error;
  }

  /**
   * Delete a label by its PDF hash.
   */
  async deleteLabel(pdfHash: string): Promise<void> {
    const { error } = await this.client
      .from("labels")
      .delete()
      .eq("pdf_hash", pdfHash);

    if (error) throw error;
  }

  /**
   * Convert a database row to a GeoLabel object.
   */
  private rowToLabel(row: any): GeoLabel {
    return {
      pdfHash: row.pdf_hash,
      pdfPath: row.pdf_path,
      corners: {
        topLeft: { lng: row.top_left_lng, lat: row.top_left_lat },
        topRight: { lng: row.top_right_lng, lat: row.top_right_lat },
        bottomRight: { lng: row.bottom_right_lng, lat: row.bottom_right_lat },
        bottomLeft: { lng: row.bottom_left_lng, lat: row.bottom_left_lat },
      },
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }
}

const db = new SupabaseDB();
export default db;
