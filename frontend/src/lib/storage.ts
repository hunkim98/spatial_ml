import { supabase } from "./supabase";

const BUCKET = "clipped-images";

function canvasToBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error("Failed to convert canvas to blob"));
    }, "image/png");
  });
}

export async function uploadClippedImage(
  pdfHash: string,
  canvas: HTMLCanvasElement
): Promise<string> {
  const blob = await canvasToBlob(canvas);
  const filePath = `${pdfHash}.png`;

  const { error } = await supabase.storage.from(BUCKET).upload(filePath, blob, {
    contentType: "image/png",
    upsert: true,
  });

  if (error) throw error;

  const { data } = supabase.storage.from(BUCKET).getPublicUrl(filePath);
  return data.publicUrl;
}

export async function deleteClippedImage(pdfHash: string): Promise<void> {
  const filePath = `${pdfHash}.png`;
  const { error } = await supabase.storage.from(BUCKET).remove([filePath]);

  if (error && !error.message.includes("not found")) {
    throw error;
  }
}
