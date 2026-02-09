import { BaseController } from "../base";
import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { CanvasEventListeners } from "../../events";

type Models = Pick<
  CanvasModel,
  "imageTransformToolModel" | "mouseInteractionModel" | "imageTransformToolModel"
>;
type Views = Pick<CanvasView, "imageLayerView">;
type ExecuteParams = {
  e: React.MouseEvent<HTMLCanvasElement>;
};

/**
 * ImageCreateToolController - handles placing a new image on canvas
 * Following clipper editor pattern: onMouseDownExecute, onMouseMoveExecute, onMouseUpExecute
 */
export class ImageCreateToolController extends BaseController<
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

    // Start creating - set initial corner
    this.models.imageTransformToolModel.isCreating = true;

    // Initialize transform corners at mouse down position
    // corner1 = top-left, corner2 = top-right, corner3 = bottom-left, corner4 = bottom-right
    this.models.imageTransformToolModel.corners = {
      corner1: { ...mouseDownWorldPosition },
      corner2: { ...mouseDownWorldPosition },
      corner3: { ...mouseDownWorldPosition },
      corner4: { ...mouseDownWorldPosition },
    };
  }

  onMouseMoveExecute(): void {
    if (!this.models.imageTransformToolModel.isCreating) return;

    const { mouseMoveWorldPosition } = this.models.mouseInteractionModel;
    const corners = this.models.imageTransformToolModel.corners;

    if (!mouseMoveWorldPosition || !corners) return;

    // Update corners to create rectangle from start to current position
    const startPoint = corners.corner1;
    const currentPoint = mouseMoveWorldPosition;

    // corner1 = top-left, corner2 = top-right, corner3 = bottom-left, corner4 = bottom-right
    this.models.imageTransformToolModel.corners = {
      corner1: startPoint,
      corner2: { x: currentPoint.x, y: startPoint.y },
      corner3: { x: startPoint.x, y: currentPoint.y },
      corner4: currentPoint,
    };
  }

  onMouseUpExecute(): void {
    this.models.imageTransformToolModel.isCreating = false;
  }
}
