/**
 * PDF file types - represents files from the data/maps directory.
 */

export interface PdfFile {
  hash: string;
  path: string;
  name: string;
  state: string;
  city: string;
}
