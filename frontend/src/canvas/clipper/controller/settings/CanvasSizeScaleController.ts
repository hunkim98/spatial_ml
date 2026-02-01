import { ClipperModel } from "../../model";
import { ClipperView } from "../../view";
import { ClipperEventListeners } from "../../events";
import { BaseController } from "../base";

type Models = Pick<ClipperModel, "pdfLayerModel" | "maskLayerModel">;

type Views = Pick<ClipperView, "pdfLayerView" | "maskLayerView">;

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
    models: ClipperModel,
    views: ClipperView,
    listeners: ClipperEventListeners
  ) {
    super(models, views, listeners);
  }

  execute(params: ExecuteParams): void {
    this.executeOnPdfCanvas(params);
    this.executeOnMaskCanvas(params);
  }

  executeOnPdfCanvas(params: ExecuteParams): void {
    const dpr = window ? window.devicePixelRatio : 1;
    const pdfLayerModel = this.models.pdfLayerModel;

    pdfLayerModel.width = params.width;
    pdfLayerModel.height = params.height;
    pdfLayerModel.dpr = dpr;

    const element = pdfLayerModel.element;
    element.style.width = `${params.width}px`;
    element.width = params.width * dpr;
    element.style.height = `${params.height}px`;
    element.height = params.height * dpr;

    console.log(dpr);
    this.views.pdfLayerView.scale(dpr);
    this.views.pdfLayerView.render();
  }

  executeOnMaskCanvas(params: ExecuteParams): void {
    const dpr = window ? window.devicePixelRatio : 1;
    const maskLayerModel = this.models.maskLayerModel;

    maskLayerModel.width = params.width;
    maskLayerModel.height = params.height;
    maskLayerModel.dpr = dpr;

    const element = maskLayerModel.element;
    element.style.width = `${params.width}px`;
    element.width = params.width * dpr;
    element.style.height = `${params.height}px`;
    element.height = params.height * dpr;

    this.views.maskLayerView.scale(dpr);
    this.views.maskLayerView.render();
  }
}
