import { BaseController } from "../base";
import { ClipperModel } from "../../model";
import { ClipperView } from "../../view";
import { ClipperEvent, ClipperEventListeners } from "../../events";

type Models = Pick<ClipperModel, "clipRectToolModel">;
type Views = Pick<ClipperView, "pdfLayerView" | "maskLayerView">;
type ExecuteParams = {
  clipRect: { x: number; y: number; width: number; height: number };
};

export class ClipRectRestoreController extends BaseController<
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
    const { x, y, width, height } = params.clipRect;

    this.models.clipRectToolModel.corner1 = { x, y };
    this.models.clipRectToolModel.corner2 = { x: x + width, y };
    this.models.clipRectToolModel.corner3 = { x, y: y + height };
    this.models.clipRectToolModel.corner4 = { x: x + width, y: y + height };

    this.views.pdfLayerView.clear();
    this.views.pdfLayerView.render();
    this.views.maskLayerView.render();

    this.dispatchEvent(ClipperEvent.CLIP_CHANGED);
  }
}
