import { CanvasEventListeners } from "../../events";
import { CanvasModel } from "../../model";
import {
  getInitialOffsetForImage,
  preprocessImageForCanvas,
} from "../../utils/image";
import { CanvasView } from "../../view";
import { BaseController } from "../base";

type Models = Pick<
  CanvasModel,
  | "imageBufferModel"
  | "editorStateModel"
  | "imageLayerModel"
  | "navigationModel"
>;
type Views = Pick<CanvasView, "imageLayerView" | "frameLayerView">;

type ExecuteParams = {
  buffer: HTMLCanvasElement | null;
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

    if (!buffer) {
      this.models.imageBufferModel.reset();
      this.models.navigationModel.reset();
      this.models.editorStateModel.isLoaded = false;
      this.views.imageLayerView.clear();
      return;
    }

    // Mark as loaded, default opacity to 0 (hidden until explicitly shown)
    this.models.editorStateModel.isLoaded = true;
    this.models.imageBufferModel.opacity = 0;
    this.models.imageLayerModel.element.style.opacity = "0";
    const canvasWidth = this.models.imageLayerModel.width;
    const canvasHeight = this.models.imageLayerModel.height;

    const { resizedImageWidth, resizedImageHeight, resizeRatio } =
      preprocessImageForCanvas(
        canvasWidth / 2,
        canvasHeight / 2,
        buffer.width,
        buffer.height
      );
    const { x, y } = getInitialOffsetForImage(
      resizedImageWidth,
      resizedImageHeight,
      canvasWidth,
      canvasHeight,
      1
    );
    this.models.imageBufferModel.update({
      buffer: buffer,
      width: buffer.width,
      height: buffer.height,
      leftTop: { x: 0, y: 0 },
    });
    this.models.navigationModel.update({
      scale: resizeRatio,
      offset: { x: x, y: y },
    });

    // Trigger render
    this.views.imageLayerView.clear();
    this.views.imageLayerView.render();
  }
}
