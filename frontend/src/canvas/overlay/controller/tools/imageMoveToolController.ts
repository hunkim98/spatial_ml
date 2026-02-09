import { BaseController } from "../base";
import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { CanvasEventListeners } from "../../events";

type Models = Pick<
  CanvasModel,
  "imageTransformToolModel" | "mouseInteractionModel"
>;
type Views = Pick<CanvasView, "imageLayerView">;
type ExecuteParams = {
  e: React.MouseEvent<HTMLCanvasElement>;
};

/**
 * ImageMoveToolController - handles moving the image on canvas
 * Following clipper editor pattern: onMouseDownExecute, onMouseMoveExecute, onMouseUpExecute
 */
export class ImageMoveToolController extends BaseController<
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
    const corners = this.models.imageTransformToolModel.corners;

    if (!mouseDownWorldPosition || !corners) return;

    // Store initial state for move calculation
    this.models.imageTransformToolModel.isEditing = true;
    this.models.imageTransformToolModel.initialCorners = {
      corner1: { ...corners.corner1 },
      corner2: { ...corners.corner2 },
      corner3: { ...corners.corner3 },
      corner4: { ...corners.corner4 },
    };
  }

  onMouseMoveExecute(): void {
    if (!this.models.imageTransformToolModel.isEditing) return;

    const { mouseDownWorldPosition, mouseMoveWorldPosition } =
      this.models.mouseInteractionModel;
    const initialCorners = this.models.imageTransformToolModel.initialCorners;

    if (!mouseDownWorldPosition || !mouseMoveWorldPosition || !initialCorners)
      return;

    // Calculate delta from start
    const dx = mouseMoveWorldPosition.x - mouseDownWorldPosition.x;
    const dy = mouseMoveWorldPosition.y - mouseDownWorldPosition.y;

    // Move all corners by delta
    this.models.imageTransformToolModel.corners = {
      corner1: {
        x: initialCorners.corner1.x + dx,
        y: initialCorners.corner1.y + dy,
      },
      corner2: {
        x: initialCorners.corner2.x + dx,
        y: initialCorners.corner2.y + dy,
      },
      corner3: {
        x: initialCorners.corner3.x + dx,
        y: initialCorners.corner3.y + dy,
      },
      corner4: {
        x: initialCorners.corner4.x + dx,
        y: initialCorners.corner4.y + dy,
      },
    };
  }

  onMouseUpExecute(): void {
    this.models.imageTransformToolModel.isEditing = false;
    this.models.imageTransformToolModel.initialCorners = null;
  }
}
