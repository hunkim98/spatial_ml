/**
 * Database schema types - mirrors the Supabase PostgreSQL schema.
 *
 * Labels use hybrid identification:
 * - pdfHash: MD5 hash of file content (primary key, stable across file moves)
 * - pdfPath: Current file path (updated if file relocates)
 */

export interface Corner {
  lng: number;
  lat: number;
}

export interface GeoLabelCorners {
  topLeft: Corner;
  topRight: Corner;
  bottomRight: Corner;
  bottomLeft: Corner;
}

export interface GeoLabel {
  pdfHash: string;
  pdfPath: string;
  corners: GeoLabelCorners;
  createdAt?: string;
  updatedAt?: string;
}

export type CornerName = keyof GeoLabelCorners;
