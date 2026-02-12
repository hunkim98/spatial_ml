import { CanvasView } from "../view";
import { CanvasModel } from "../model";
import { CanvasEventListeners } from "../events";
import { BaseController } from "./base";

type Models = Pick<CanvasModel, "imageLayerModel" | "imageBufferModel">;
type Views = Pick<CanvasView, "imageLayerView">;
type ExecuteParams = {
  opacity?: number;
  visible?: boolean;
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
    if (params.opacity !== undefined) {
      this.models.imageBufferModel.opacity = params.opacity;
    }
    if (params.visible !== undefined) {
      this.models.imageLayerModel.element.style.opacity = params.visible
        ? "1"
        : "0";
    }
  }
}
