import { getPdfPageAsBlob } from "@/lib/pdf";
import { ClipperEventListeners } from "../events";
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
  padding?: number; // 0-1, percentage of canvas to use (default 0.9)
  resourceUrl: string;
  pageNumber: number;
  canvasWidth: number;
  canvasHeight: number;
};

export class PdfUpdateController extends BaseController<
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
    const { resourceUrl, pageNumber, canvasWidth, canvasHeight } = params;
    this.models.editorStatusModel.isLoading = true;

    const { blob, url } = await getPdfPageAsBlob(resourceUrl, pageNumber);
    const image = await this._loadImage(url);
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
      blob: blob,
      blobUrl: url,
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
