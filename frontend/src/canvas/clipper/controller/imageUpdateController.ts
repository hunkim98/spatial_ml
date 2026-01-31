import { ClipperEventListeners } from "../events";
import { ClipperModel } from "../model";
import { ClipperView } from "../view";
import { BaseController } from "./base";

type Models = Pick<ClipperModel, "pdfLayerModel" | "imageModel" | "navigationModel">;
type Views = Pick<ClipperView, "pdfLayerView" | "maskLayerView">;

type ExecuteParams = {
  padding?: number; // 0-1, percentage of canvas to use (default 0.9)
};

export class ImageUpdateController extends BaseController<
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

  execute(params: ExecuteParams = {}): void {
    const { padding = 0.9 } = params;

    const { width: imageWidth, height: imageHeight } = this.models.imageModel;
    const { element } = this.models.pdfLayerModel;
    const canvasWidth = element.width;
    const canvasHeight = element.height;

    if (imageWidth === 0 || imageHeight === 0) return;

    // Calculate scale to fit image in canvas
    const scaleX = (canvasWidth * padding) / imageWidth;
    const scaleY = (canvasHeight * padding) / imageHeight;
    const scale = Math.min(scaleX, scaleY);

    // Calculate offset to center the image
    const offsetX = (canvasWidth - imageWidth * scale) / 2;
    const offsetY = (canvasHeight - imageHeight * scale) / 2;

    this.models.navigationModel.scale = scale;
    this.models.navigationModel.offset = { x: offsetX, y: offsetY };

    this.views.pdfLayerView.clear();
    this.views.pdfLayerView.render();
    this.views.maskLayerView.render();
  }
}
