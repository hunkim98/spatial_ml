import { BaseController } from "../base";
import { ClipperModel } from "../../model";
import { ClipperView } from "../../view";
import { ClipperEventListeners } from "../../events";

type Models = Pick<
  ClipperModel,
  "clipRectToolModel" | "mouseInteractionModel"
>;
type Views = Pick<ClipperView, "maskLayerView">;
type ExecuteParams = {
  e: React.MouseEvent<HTMLCanvasElement>;
};

export class ClipRectCreateToolController extends BaseController<
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
    const { e } = params;
    if (e.type === "mousedown") {
      this.onMouseDownExecute();
    } else if (e.type === "mousemove") {
      this.onMouseMoveExecute();
    } else if (e.type === "mouseup") {
      this.onMouseUpExecute();
    }
  }

  onMouseDownExecute(): void {
    const { mouseDownWorldPosition } = this.models.mouseInteractionModel;
    if (!mouseDownWorldPosition) return;
    this.models.clipRectToolModel.corner1 = {
      x: mouseDownWorldPosition.x,
      y: mouseDownWorldPosition.y,
    };
    this.models.clipRectToolModel.isCreating = true;
  }

  onMouseMoveExecute(): void {
    if (!this.models.clipRectToolModel.isCreating) return;

    const { mouseMoveWorldPosition } = this.models.mouseInteractionModel;
    const { corner1 } = this.models.clipRectToolModel;

    if (!mouseMoveWorldPosition || !corner1) return;

    this.models.clipRectToolModel.corner2 = {
      x: mouseMoveWorldPosition.x,
      y: corner1.y,
    };
    this.models.clipRectToolModel.corner3 = {
      x: corner1.x,
      y: mouseMoveWorldPosition.y,
    };
    this.models.clipRectToolModel.corner4 = {
      x: mouseMoveWorldPosition.x,
      y: mouseMoveWorldPosition.y,
    };
  }

  onMouseUpExecute(): void {
    this.models.clipRectToolModel.isCreating = false;
  }
}
