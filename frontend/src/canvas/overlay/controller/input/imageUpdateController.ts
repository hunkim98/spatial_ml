import { CanvasEventListeners } from "../../events";
import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { BaseController } from "../base";

type Models = Pick<CanvasModel, "imageBufferModel" | "editorStateModel">;
type Views = Pick<CanvasView, "imageLayerView" | "frameLayerView">;

type ExecuteParams = {
  url: string;
};

export class ImageUpdateController extends BaseController<
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

  async execute(params: ExecuteParams): Promise<void> {
    const { url } = params;
    this.models.editorStateModel.isLoaded = false;

    return new Promise((resolve, reject) => {
      const img = new Image();

      img.crossOrigin = "anonymous";
      img.onload = () => {
        const buffer = document.createElement("canvas");
        buffer.width = img.naturalWidth;
        buffer.height = img.naturalHeight;

        const ctx = buffer.getContext("2d");
        if (!ctx) return reject(new Error("Could not get buffer context"));

        ctx.drawImage(img, 0, 0);

        this.models.imageBufferModel.buffer = buffer;
        this.models.imageBufferModel.width = img.naturalWidth;
        this.models.imageBufferModel.height = img.naturalHeight;
        this.models.editorStateModel.isLoaded = true;

        // Re-render with new content
        this.views.imageLayerView.clear();
        this.views.imageLayerView.render();
        this.views.frameLayerView.clear();
        this.views.frameLayerView.render();

        resolve();
      };
      img.onerror = reject;
      img.src = url;
    });
  }
}
