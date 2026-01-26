import { Pool } from "pg";

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
  private pool: Pool;
  private initialized = false;

  constructor() {
    this.pool = new Pool({
      connectionString: process.env.DATABASE_URL,
      ssl: { rejectUnauthorized: false },
    });
  }

  /**
   * Initialize the database schema.
   * Creates the labels table with pdf_hash as the unique key.
   * pdf_path is stored for display but can be updated if files move.
   */
  private async init() {
    if (this.initialized) return;

    const client = await this.pool.connect();
    try {
      await client.query(`
        CREATE TABLE IF NOT EXISTS labels (
          id SERIAL PRIMARY KEY,
          pdf_hash TEXT UNIQUE NOT NULL,
          pdf_path TEXT NOT NULL,
          top_left_lng DOUBLE PRECISION NOT NULL,
          top_left_lat DOUBLE PRECISION NOT NULL,
          top_right_lng DOUBLE PRECISION NOT NULL,
          top_right_lat DOUBLE PRECISION NOT NULL,
          bottom_right_lng DOUBLE PRECISION NOT NULL,
          bottom_right_lat DOUBLE PRECISION NOT NULL,
          bottom_left_lng DOUBLE PRECISION NOT NULL,
          bottom_left_lat DOUBLE PRECISION NOT NULL,
          created_at TIMESTAMP DEFAULT NOW(),
          updated_at TIMESTAMP DEFAULT NOW()
        )
      `);
      this.initialized = true;
    } finally {
      client.release();
    }
  }

  /**
   * Get all labels from the database.
   * Returns a map keyed by pdf_hash for easy lookup.
   */
  async getAllLabels(): Promise<Record<string, GeoLabel>> {
    await this.init();
    const client = await this.pool.connect();
    try {
      const result = await client.query(
        "SELECT * FROM labels ORDER BY updated_at DESC"
      );
      const labels: Record<string, GeoLabel> = {};
      for (const row of result.rows) {
        labels[row.pdf_hash] = this.rowToLabel(row);
      }
      return labels;
    } finally {
      client.release();
    }
  }

  /**
   * Get a label by its PDF hash.
   */
  async getLabelByHash(pdfHash: string): Promise<GeoLabel | null> {
    await this.init();
    const client = await this.pool.connect();
    try {
      const result = await client.query(
        "SELECT * FROM labels WHERE pdf_hash = $1",
        [pdfHash]
      );
      if (result.rows.length === 0) return null;
      return this.rowToLabel(result.rows[0]);
    } finally {
      client.release();
    }
  }

  /**
   * Save or update a label.
   * Uses pdf_hash as the unique key (ON CONFLICT).
   * If the same hash exists with a different path, the path is updated.
   */
  async saveLabel(label: GeoLabel): Promise<void> {
    await this.init();
    const client = await this.pool.connect();
    try {
      await client.query(
        `INSERT INTO labels (
          pdf_hash, pdf_path,
          top_left_lng, top_left_lat,
          top_right_lng, top_right_lat,
          bottom_right_lng, bottom_right_lat,
          bottom_left_lng, bottom_left_lat,
          updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
        ON CONFLICT (pdf_hash) DO UPDATE SET
          pdf_path = $2,
          top_left_lng = $3, top_left_lat = $4,
          top_right_lng = $5, top_right_lat = $6,
          bottom_right_lng = $7, bottom_right_lat = $8,
          bottom_left_lng = $9, bottom_left_lat = $10,
          updated_at = NOW()`,
        [
          label.pdfHash,
          label.pdfPath,
          label.corners.topLeft.lng,
          label.corners.topLeft.lat,
          label.corners.topRight.lng,
          label.corners.topRight.lat,
          label.corners.bottomRight.lng,
          label.corners.bottomRight.lat,
          label.corners.bottomLeft.lng,
          label.corners.bottomLeft.lat,
        ]
      );
    } finally {
      client.release();
    }
  }

  /**
   * Delete a label by its PDF hash.
   */
  async deleteLabel(pdfHash: string): Promise<void> {
    await this.init();
    const client = await this.pool.connect();
    try {
      await client.query("DELETE FROM labels WHERE pdf_hash = $1", [pdfHash]);
    } finally {
      client.release();
    }
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
      createdAt: row.created_at?.toISOString(),
      updatedAt: row.updated_at?.toISOString(),
    };
  }
}

const db = new SupabaseDB();
export default db;
