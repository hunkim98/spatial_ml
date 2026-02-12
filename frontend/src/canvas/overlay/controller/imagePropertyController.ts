import { CanvasView } from "../view";
import { CanvasModel } from "../model";
import { CanvasEventListeners } from "../events";
import { BaseController } from "./base";

type Models = Pick<CanvasModel, "imageLayerModel" | "imageBufferModel">;
type Views = Pick<CanvasView, "imageLayerView">;
type ExecuteParams = {
  opacity: number;
};

export class ImagePropertyController extends BaseController<
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
    const { opacity } = params;
    this.models.imageBufferModel.opacity = opacity;
    this.models.imageLayerModel.element.style.opacity = String(opacity);
  }
}
