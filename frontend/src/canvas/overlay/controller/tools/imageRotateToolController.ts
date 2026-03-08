import { BaseController } from "../base";
import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { CanvasEventListeners } from "../../events";
import { Point, ScreenCorners } from "../../types";

type Models = Pick<
  CanvasModel,
  "imageTransformToolModel" | "mouseInteractionModel"
>;
type Views = Pick<CanvasView, "imageLayerView">;
type ExecuteParams = {
  e: React.MouseEvent<Element>;
};

/**
 * ImageRotateToolController - handles rotating the image around its center
 * Following clipper editor pattern: onMouseDownExecute, onMouseMoveExecute, onMouseUpExecute
 */
export class ImageRotateToolController extends BaseController<
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
    const corners = this.models.imageTransformToolModel.corners;
    if (!corners) return;

    // Store initial state for rotation calculation
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

    const center = this.getCenter(initialCorners);

    // Calculate angle from center to drag start
    const startAngle = Math.atan2(
      mouseDownWorldPosition.y - center.y,
      mouseDownWorldPosition.x - center.x
    );

    // Calculate angle from center to current point
    const currentAngle = Math.atan2(
      mouseMoveWorldPosition.y - center.y,
      mouseMoveWorldPosition.x - center.x
    );

    // Rotation delta
    const deltaAngle = currentAngle - startAngle;

    // Rotate all corners around center
    this.models.imageTransformToolModel.corners = this.rotateCorners(
      initialCorners,
      center,
      deltaAngle
    );
  }

  onMouseUpExecute(): void {
    this.models.imageTransformToolModel.isEditing = false;
    this.models.imageTransformToolModel.initialCorners = null;
  }

  private getCenter(corners: ScreenCorners): Point {
    return {
      x:
        (corners.corner1.x +
          corners.corner2.x +
          corners.corner3.x +
          corners.corner4.x) /
        4,
      y:
        (corners.corner1.y +
          corners.corner2.y +
          corners.corner3.y +
          corners.corner4.y) /
        4,
    };
  }

  private rotateCorners(
    corners: ScreenCorners,
    center: Point,
    angle: number
  ): ScreenCorners {
    return {
      corner1: this.rotatePoint(corners.corner1, center, angle),
      corner2: this.rotatePoint(corners.corner2, center, angle),
      corner3: this.rotatePoint(corners.corner3, center, angle),
      corner4: this.rotatePoint(corners.corner4, center, angle),
    };
  }

  private rotatePoint(point: Point, center: Point, angle: number): Point {
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);

    const dx = point.x - center.x;
    const dy = point.y - center.y;

    return {
      x: center.x + dx * cos - dy * sin,
      y: center.y + dx * sin + dy * cos,
    };
  }
}
