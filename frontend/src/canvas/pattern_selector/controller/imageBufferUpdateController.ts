import {
  PatternSelectorEvent,
  PatternSelectorEventListeners,
} from "../events";
import { PatternSelectorModel } from "../model";
import { PatternSelectorView } from "../view";
import { BaseController } from "./base";

type Models = Pick<
  PatternSelectorModel,
  | "imageModel"
  | "imageLayerModel"
  | "navigationModel"
  | "editorStatusModel"
>;
type Views = Pick<
  PatternSelectorView,
  "imageLayerView" | "overlayLayerView"
>;

type ExecuteParams = {
  imageUrl: string;
};

/**
 * Loads an image from a URL (e.g. object URL from uploaded file).
 * Loads it into an HTMLImageElement and centers it in the viewport.
 */
export class ImageBufferUpdateController extends BaseController<
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
    const { imageUrl } = params;

    const img = new Image();
    img.onload = () => {
      this.models.imageModel.image = img;
      this.models.imageModel.width = img.naturalWidth;
      this.models.imageModel.height = img.naturalHeight;
      this.models.imageModel.leftTop = { x: 0, y: 0 };

      // Fit image in viewport
      const canvasW = this.models.imageLayerModel.width;
      const canvasH = this.models.imageLayerModel.height;
      const scaleX = canvasW / img.naturalWidth;
      const scaleY = canvasH / img.naturalHeight;
      const scale = Math.min(scaleX, scaleY) * 0.9;

      this.models.navigationModel.scale = scale;
      this.models.navigationModel.offset = {
        x: (canvasW - img.naturalWidth * scale) / 2,
        y: (canvasH - img.naturalHeight * scale) / 2,
      };

      this.models.editorStatusModel.isLoaded = true;

      this.views.imageLayerView.clear();
      this.views.imageLayerView.render();
      this.views.overlayLayerView.render();

      this.dispatchEvent(PatternSelectorEvent.IMAGE_LOADED);
    };
    img.src = imageUrl;
  }
}
