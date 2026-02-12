import { BaseController } from "../base";
import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { CanvasEventListeners } from "../../events";

type Models = Pick<
  CanvasModel,
  | "imageTransformToolModel"
  | "mouseInteractionModel"
  | "imageBufferModel"
  | "toolManagerModel"
>;
type Views = Pick<CanvasView, "imageLayerView">;
type ExecuteParams = {
  e: React.MouseEvent<Element>;
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

    // Initialize transform corners at mouse down position
    // corner1 = top-left, corner2 = top-right, corner3 = bottom-left, corner4 = bottom-right
    this.models.imageTransformToolModel.corners = {
      corner1: { ...mouseDownWorldPosition },
      corner2: { ...mouseDownWorldPosition },
      corner3: { ...mouseDownWorldPosition },
      corner4: { ...mouseDownWorldPosition },
    };
    this.models.imageTransformToolModel.isCreating = true;
  }

  onMouseMoveExecute(): void {
    if (!this.models.imageTransformToolModel.isCreating) return;

    const { mouseMoveWorldPosition } = this.models.mouseInteractionModel;
    const corners = this.models.imageTransformToolModel.corners;
    const { width: imageWidth, height: imageHeight } =
      this.models.imageBufferModel;

    if (!mouseMoveWorldPosition || !corners || !imageWidth || !imageHeight)
      return;

    // Calculate image aspect ratio
    const aspectRatio = imageWidth / imageHeight;

    // Update corners to create rectangle from start to current position
    const startPoint = corners.corner1;
    const currentPoint = mouseMoveWorldPosition;

    // Calculate dimensions
    let width = currentPoint.x - startPoint.x;
    let height = currentPoint.y - startPoint.y;

    // Constrain to aspect ratio based on the larger dimension
    if (Math.abs(width) / aspectRatio > Math.abs(height)) {
      // Width is constraining - adjust height
      height = width / aspectRatio;
    } else {
      // Height is constraining - adjust width
      width = height * aspectRatio;
    }

    // corner1 = top-left, corner2 = top-right, corner3 = bottom-left, corner4 = bottom-right
    this.models.imageTransformToolModel.corners = {
      corner1: startPoint,
      corner2: { x: startPoint.x + width, y: startPoint.y },
      corner3: { x: startPoint.x, y: startPoint.y + height },
      corner4: { x: startPoint.x + width, y: startPoint.y + height },
    };
  }

  onMouseUpExecute(): void {
    this.models.imageTransformToolModel.isCreating = false;
    this.models.toolManagerModel.forcedTool = null;
  }
}
