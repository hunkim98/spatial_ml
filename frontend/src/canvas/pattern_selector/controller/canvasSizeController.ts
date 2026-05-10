import { PatternSelectorEventListeners } from "../events";
import { PatternSelectorModel } from "../model";
import { PatternSelectorView } from "../view";
import { BaseController } from "./base";

type Models = Pick<
  PatternSelectorModel,
  "imageLayerModel" | "overlayLayerModel"
>;
type Views = Pick<
  PatternSelectorView,
  "imageLayerView" | "overlayLayerView"
>;

type ExecuteParams = {
  width: number;
  height: number;
};

export class CanvasSizeController extends BaseController<
  Models,
  Views,
  ExecuteParams
> {
  constructor(
    models: PatternSelectorModel,
    views: PatternSelectorView,
    listeners: PatternSelectorEventListeners
  ) {
    super(models, views, listeners);
  }

  execute(params: ExecuteParams): void {
    this.resizeLayer(
      this.models.imageLayerModel,
      this.views.imageLayerView,
      params
    );
    this.resizeLayer(
      this.models.overlayLayerModel,
      this.views.overlayLayerView,
      params
    );
  }

  private resizeLayer(
    layerModel: { width: number; height: number; dpr: number; element: HTMLCanvasElement },
    layerView: { scale: (dpr: number) => void; render: () => void },
    params: ExecuteParams
  ): void {
    const dpr = window ? window.devicePixelRatio : 1;

    layerModel.width = params.width;
    layerModel.height = params.height;
    layerModel.dpr = dpr;

    const element = layerModel.element;
    element.style.width = `${params.width}px`;
    element.width = params.width * dpr;
    element.style.height = `${params.height}px`;
    element.height = params.height * dpr;

    layerView.scale(dpr);
    layerView.render();
  }
}
