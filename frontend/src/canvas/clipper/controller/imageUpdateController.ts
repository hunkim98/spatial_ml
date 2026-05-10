import { ClipperEvent, ClipperEventListeners } from "../events";
import { ClipperModel } from "../model";
import { ClipperView } from "../view";
import { BaseController } from "./base";
import {
  getInitialOffsetForImage,
  preprocessImageForCanvas,
} from "../utils/image";

type Models = Pick<
  ClipperModel,
  "pdfLayerModel" | "imageModel" | "navigationModel" | "editorStatusModel"
>;
type Views = Pick<ClipperView, "pdfLayerView" | "maskLayerView">;

type ExecuteParams = {
  imageUrl: string;
  padding?: number;
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

  async execute(params: ExecuteParams): Promise<void> {
    const { imageUrl } = params;
    const canvasWidth = this.models.pdfLayerModel.width;
    const canvasHeight = this.models.pdfLayerModel.height;
    this.models.editorStatusModel.isLoading = true;

    const image = await this._loadImage(imageUrl);
    const { resizedImageWidth, resizedImageHeight, resizeRatio } =
      preprocessImageForCanvas(
        canvasWidth / 2,
        canvasHeight / 2,
        image.width,
        image.height
      );
    const { x, y } = getInitialOffsetForImage(
      resizedImageWidth,
      resizedImageHeight,
      canvasWidth,
      canvasHeight,
      1
    );
    this.models.imageModel.update({
      image: image,
      blob: null,
      blobUrl: imageUrl,
      width: image.width,
      height: image.height,
      leftTop: { x: 0, y: 0 },
    });
    this.models.navigationModel.update({
      scale: resizeRatio,
      offset: { x: x, y: y },
    });
    this.models.editorStatusModel.isLoaded = true;

    this.views.pdfLayerView.clear();
    this.views.pdfLayerView.render();
    this.views.maskLayerView.render();

    // Reuse the same event so existing sidebar listeners work
    this.dispatchEvent(ClipperEvent.PDF_LOADED);
  }

  private _loadImage(url: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("Failed to load image"));
      img.src = url;
    });
  }
}
