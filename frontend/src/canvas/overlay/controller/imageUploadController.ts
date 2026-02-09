import { BaseController } from "./base";
import { CanvasModel } from "../model";
import { CanvasView } from "../view";
import { CanvasEventListeners } from "../events";

type Models = Pick<CanvasModel, "imageBufferModel" | "editorStateModel">;
type Views = Pick<CanvasView, "imageLayerView">;

export interface ImageUploadParams {
  buffer: HTMLCanvasElement;
}

/**
 * ImageUploadController - uploads/loads image buffer into editor
 * Similar to PdfUpdateController in clipper editor
 * Following MVC pattern: updates models, triggers view render
 */
export class ImageUploadController extends BaseController<
  Models,
  Views,
  ImageUploadParams
> {
  constructor(
    models: CanvasModel,
    views: CanvasView,
    listeners: CanvasEventListeners
  ) {
    super(models, views, listeners);
  }

  execute(params: ImageUploadParams): void {
    const { buffer } = params;

    // Update model with image buffer
    this.models.imageBufferModel.buffer = buffer;
    this.models.imageBufferModel.width = buffer.width;
    this.models.imageBufferModel.height = buffer.height;

    // Mark as loaded
    this.models.editorStateModel.isLoaded = true;

    // Trigger render
    this.views.imageLayerView.render();
  }
}
