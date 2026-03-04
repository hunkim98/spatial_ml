CREATE TABLE public.skipped_labels (
  pdf_hash TEXT PRIMARY KEY,
  pdf_path TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
