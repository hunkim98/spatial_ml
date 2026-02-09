import { CanvasEventListeners } from "../../events";
import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { BaseController } from "../base";

type Models = Pick<CanvasModel, "imageBufferModel" | "editorStateModel">;
type Views = Pick<CanvasView, "imageLayerView" | "frameLayerView">;

type ExecuteParams = {
  buffer: HTMLCanvasElement;
};

export class BufferUpdateController extends BaseController<
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

  execute(params: ExecuteParams): void {
    const { buffer } = params;

    this.models.imageBufferModel.buffer = buffer;
    this.models.imageBufferModel.width = buffer.width;
    this.models.imageBufferModel.height = buffer.height;
    this.models.editorStateModel.isLoaded = true;

    // Re-render with new content
    this.views.imageLayerView.clear();
    this.views.imageLayerView.render();
    this.views.frameLayerView.clear();
    this.views.frameLayerView.render();
  }
}
