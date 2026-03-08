INSERT INTO storage.buckets (id, name, public)
VALUES ('clipped-images', 'clipped-images', true)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Allow public read access"
ON storage.objects FOR SELECT
USING (bucket_id = 'clipped-images');

CREATE POLICY "Allow public upload"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'clipped-images');

CREATE POLICY "Allow public update"
ON storage.objects FOR UPDATE
USING (bucket_id = 'clipped-images');
