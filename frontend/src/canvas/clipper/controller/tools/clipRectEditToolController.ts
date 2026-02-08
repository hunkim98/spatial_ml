import { BaseController } from "../base";
import { ClipperModel } from "../../model";
import { ClipperView } from "../../view";
import { ClipperEventListeners } from "../../events";
import { HandleType } from "../../types";

type Models = Pick<ClipperModel, "clipRectToolModel" | "mouseInteractionModel">;
type Views = Pick<ClipperView, "maskLayerView">;
type ExecuteParams = {
  e: React.MouseEvent<HTMLCanvasElement>;
};

export class ClipRectEditToolController extends BaseController<
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
    const { activeHandle } = this.models.clipRectToolModel;
    if (!activeHandle) return;
    this.models.clipRectToolModel.isEditing = true;
  }

  onMouseMoveExecute(): void {
    if (!this.models.clipRectToolModel.isEditing) return;

    const { mouseMoveWorldPosition } = this.models.mouseInteractionModel;
    const { activeHandle, rect } = this.models.clipRectToolModel;

    if (!mouseMoveWorldPosition || !activeHandle || !rect) {
      return;
    }

    const mousePos = mouseMoveWorldPosition;

    // Get current rect bounds
    let minX = rect.offset.x;
    let minY = rect.offset.y;
    let maxX = rect.offset.x + rect.width;
    let maxY = rect.offset.y + rect.height;

    // Update bounds based on which handle is being dragged
    switch (activeHandle) {
      case HandleType.TOP_LEFT:
        minX = mousePos.x;
        minY = mousePos.y;
        break;
      case HandleType.TOP_RIGHT:
        maxX = mousePos.x;
        minY = mousePos.y;
        break;
      case HandleType.BOTTOM_RIGHT:
        maxX = mousePos.x;
        maxY = mousePos.y;
        break;
      case HandleType.BOTTOM_LEFT:
        minX = mousePos.x;
        maxY = mousePos.y;
        break;
      case HandleType.LEFT:
        minX = mousePos.x;
        break;
      case HandleType.RIGHT:
        maxX = mousePos.x;
        break;
      case HandleType.TOP:
        minY = mousePos.y;
        break;
      case HandleType.BOTTOM:
        maxY = mousePos.y;
        break;
    }

    // Update corners based on new bounds
    // corner1 = top-left, corner4 = bottom-right
    this.models.clipRectToolModel.corner1 = { x: minX, y: minY };
    this.models.clipRectToolModel.corner2 = { x: maxX, y: minY };
    this.models.clipRectToolModel.corner3 = { x: minX, y: maxY };
    this.models.clipRectToolModel.corner4 = { x: maxX, y: maxY };
  }

  onMouseUpExecute(): void {
    this.models.clipRectToolModel.isEditing = false;
  }
}
