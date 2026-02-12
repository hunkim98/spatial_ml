import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { CanvasEventListeners } from "../../events";
import { BaseController } from "../base";

type Models = Pick<CanvasModel, "imageLayerModel" | "frameLayerModel">;

type Views = Pick<CanvasView, "imageLayerView" | "frameLayerView">;

type ExecuteParams = {
  width: number;
  height: number;
};

export class CanvasSizeScaleController extends BaseController<
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
    this.executeOnImageCanvas(params);
    this.executeOnFrameCanvas(params);
  }

  executeOnImageCanvas(params: ExecuteParams): void {
    const dpr = window ? window.devicePixelRatio : 1;
    const imageLayerModel = this.models.imageLayerModel;

    imageLayerModel.width = params.width;
    imageLayerModel.height = params.height;
    imageLayerModel.dpr = dpr;

    const element = imageLayerModel.element;
    element.style.width = `${params.width}px`;
    element.width = params.width * dpr;
    element.style.height = `${params.height}px`;
    element.height = params.height * dpr;

    this.views.imageLayerView.scale(dpr);
    this.views.imageLayerView.render();
  }

  executeOnFrameCanvas(params: ExecuteParams): void {
    const dpr = window ? window.devicePixelRatio : 1;
    const frameLayerModel = this.models.frameLayerModel;

    frameLayerModel.width = params.width;
    frameLayerModel.height = params.height;
    frameLayerModel.dpr = dpr;

    const element = frameLayerModel.element;
    element.style.width = `${params.width}px`;
    element.width = params.width * dpr;
    element.style.height = `${params.height}px`;
    element.height = params.height * dpr;

    this.views.frameLayerView.scale(dpr);
    this.views.frameLayerView.render();
  }
}
