// pdfjs-dist is loaded dynamically to avoid SSR issues
let pdfjs: typeof import("pdfjs-dist") | null = null;

async function getPdfjs() {
  if (!pdfjs) {
    pdfjs = await import("pdfjs-dist");
    pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
  }
  return pdfjs;
}

async function getPdfPageAsCanvas(
  pdfUrl: string,
  pageNumber: number,
  scale: number = 2
): Promise<HTMLCanvasElement> {
  const pdfjsLib = await getPdfjs();
  const pdf = await pdfjsLib.getDocument(pdfUrl).promise;
  const page = await pdf.getPage(pageNumber);
  const viewport = page.getViewport({ scale });

  const canvas = document.createElement("canvas");
  canvas.width = viewport.width;
  canvas.height = viewport.height;

  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Could not get canvas context");

  await page.render({
    canvasContext: ctx,
    viewport,
    canvas,
  }).promise;

  return canvas;
}

export async function getPdfPageAsBlob(
  pdfUrl: string,
  pageNumber: number,
  scale: number = 2,
  format: "image/png" | "image/jpeg" = "image/png"
): Promise<{ blob: Blob; url: string; width: number; height: number }> {
  const canvas = await getPdfPageAsCanvas(pdfUrl, pageNumber, scale);

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error("Failed to convert canvas to blob"));
        return;
      }
      resolve({
        blob,
        url: URL.createObjectURL(blob),
        width: canvas.width,
        height: canvas.height,
      });
    }, format);
  });
}
