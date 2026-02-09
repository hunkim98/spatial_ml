import { CanvasEventListeners } from "../../events";
import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { BaseController } from "../base";

// pdfjs-dist is loaded dynamically to avoid SSR issues
let pdfjs: typeof import("pdfjs-dist") | null = null;

async function getPdfjs() {
  if (!pdfjs) {
    pdfjs = await import("pdfjs-dist");
    pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
  }
  return pdfjs;
}

type Models = Pick<CanvasModel, "imageBufferModel" | "editorStateModel">;
type Views = Pick<CanvasView, "imageLayerView" | "frameLayerView">;

type ExecuteParams = {
  url: string;
  pageNumber: number;
};

export class PdfUpdateController extends BaseController<
  Models,
  Views,
  ExecuteParams
> {
  constructor(
    models: CanvasModel,
    views: CanvasView,
    listeners: CanvasEventListeners
  ) {
    super(models, views, listeners);
  }

  async execute(params: ExecuteParams): Promise<void> {
    const { url, pageNumber } = params;
    this.models.editorStateModel.isLoaded = false;

    const pdfjsLib = await getPdfjs();
    const pdf = await pdfjsLib.getDocument(url).promise;
    const page = await pdf.getPage(pageNumber);
    const viewport = page.getViewport({ scale: 2 });

    const buffer = document.createElement("canvas");
    buffer.width = viewport.width;
    buffer.height = viewport.height;

    const ctx = buffer.getContext("2d");
    if (!ctx) throw new Error("Could not get buffer context");

    await page.render({
      canvasContext: ctx,
      viewport,
      canvas: buffer,
    }).promise;

    this.models.imageBufferModel.buffer = buffer;
    this.models.imageBufferModel.width = viewport.width;
    this.models.imageBufferModel.height = viewport.height;
    this.models.editorStateModel.isLoaded = true;

    // Re-render with new content
    this.views.imageLayerView.clear();
    this.views.imageLayerView.render();
    this.views.frameLayerView.clear();
    this.views.frameLayerView.render();
  }
}
