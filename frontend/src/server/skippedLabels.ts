import { getSupabaseClient } from "@/server/supabase";
import { SkippedLabel } from "@/types/labels";

// ========== Row Mapping ==========

function rowToSkippedLabel(row: any): SkippedLabel {
  return {
    pdfHash: row.pdf_hash,
    pdfPath: row.pdf_path,
    createdAt: row.created_at,
  };
}

// ========== Skipped Labels CRUD ==========

export async function getAllSkippedLabels(): Promise<
  Record<string, SkippedLabel>
> {
  const client = getSupabaseClient();
  const { data, error } = await client
    .from("skipped_labels")
    .select("*")
    .order("created_at", { ascending: false });

  if (error) throw error;

  const skipped: Record<string, SkippedLabel> = {};
  for (const row of data) {
    skipped[row.pdf_hash] = rowToSkippedLabel(row);
  }
  return skipped;
}

export async function skipLabel(
  pdfHash: string,
  pdfPath: string
): Promise<void> {
  const client = getSupabaseClient();
  const { error } = await client.from("skipped_labels").upsert(
    {
      pdf_hash: pdfHash,
      pdf_path: pdfPath,
    },
    { onConflict: "pdf_hash" }
  );

  if (error) throw error;
}

export async function unskipLabel(pdfHash: string): Promise<void> {
  const client = getSupabaseClient();
  const { error } = await client
    .from("skipped_labels")
    .delete()
    .eq("pdf_hash", pdfHash);

  if (error) throw error;
}
