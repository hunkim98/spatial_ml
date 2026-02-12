import { BaseController } from "../base";
import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { CanvasEventListeners } from "../../events";
import { Point, HandleType, ScreenCorners } from "../../types";

type Models = Pick<
  CanvasModel,
  "imageTransformToolModel" | "mouseInteractionModel" | "imageBufferModel"
>;
type Views = Pick<CanvasView, "imageLayerView">;
type ExecuteParams = {
  e: React.MouseEvent<Element>;
};

/**
 * ImageResizeToolController - handles resizing the image by dragging corner handles
 * Following clipper editor pattern: onMouseDownExecute, onMouseMoveExecute, onMouseUpExecute
 */
export class ImageResizeToolController extends BaseController<
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

    // Store initial state for resize calculation
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

    const { mouseMoveWorldPosition } = this.models.mouseInteractionModel;
    const initialCorners = this.models.imageTransformToolModel.initialCorners;
    const activeHandle = this.models.imageTransformToolModel.activeHandle;
    const { width: imageWidth, height: imageHeight } =
      this.models.imageBufferModel;

    if (
      !mouseMoveWorldPosition ||
      !initialCorners ||
      !activeHandle ||
      !imageWidth ||
      !imageHeight
    )
      return;

    // Calculate image aspect ratio
    const aspectRatio = imageWidth / imageHeight;

    // Get anchor (opposite corner)
    const anchor = this.getAnchorPoint(initialCorners, activeHandle);

    // Calculate new dimensions from anchor to mouse position
    let width = Math.abs(mouseMoveWorldPosition.x - anchor.x);
    let height = Math.abs(mouseMoveWorldPosition.y - anchor.y);

    // Constrain to aspect ratio based on the larger dimension
    if (width / aspectRatio > height) {
      // Width is constraining - adjust height
      height = width / aspectRatio;
    } else {
      // Height is constraining - adjust width
      width = height * aspectRatio;
    }

    // Determine the direction of the resize based on which corner is being dragged
    const signX = mouseMoveWorldPosition.x >= anchor.x ? 1 : -1;
    const signY = mouseMoveWorldPosition.y >= anchor.y ? 1 : -1;

    // Calculate new corners maintaining axis alignment and aspect ratio
    const newCorners: ScreenCorners = {
      corner1: { x: 0, y: 0 },
      corner2: { x: 0, y: 0 },
      corner3: { x: 0, y: 0 },
      corner4: { x: 0, y: 0 },
    };

    // Position corners based on anchor and signs
    if (signX > 0 && signY > 0) {
      // Bottom-right from anchor
      newCorners.corner1 = anchor;
      newCorners.corner2 = { x: anchor.x + width, y: anchor.y };
      newCorners.corner3 = { x: anchor.x, y: anchor.y + height };
      newCorners.corner4 = { x: anchor.x + width, y: anchor.y + height };
    } else if (signX < 0 && signY > 0) {
      // Bottom-left from anchor
      newCorners.corner1 = { x: anchor.x - width, y: anchor.y };
      newCorners.corner2 = anchor;
      newCorners.corner3 = { x: anchor.x - width, y: anchor.y + height };
      newCorners.corner4 = { x: anchor.x, y: anchor.y + height };
    } else if (signX > 0 && signY < 0) {
      // Top-right from anchor
      newCorners.corner1 = { x: anchor.x, y: anchor.y - height };
      newCorners.corner2 = { x: anchor.x + width, y: anchor.y - height };
      newCorners.corner3 = anchor;
      newCorners.corner4 = { x: anchor.x + width, y: anchor.y };
    } else {
      // Top-left from anchor
      newCorners.corner1 = { x: anchor.x - width, y: anchor.y - height };
      newCorners.corner2 = { x: anchor.x, y: anchor.y - height };
      newCorners.corner3 = { x: anchor.x - width, y: anchor.y };
      newCorners.corner4 = anchor;
    }

    this.models.imageTransformToolModel.corners = newCorners;
  }

  onMouseUpExecute(): void {
    this.models.imageTransformToolModel.isEditing = false;
    this.models.imageTransformToolModel.initialCorners = null;
  }

  private getAnchorPoint(corners: ScreenCorners, handle: HandleType): Point {
    // Return opposite corner as anchor
    switch (handle) {
      case HandleType.TOP_LEFT:
        return corners.corner4; // opposite of corner1 is corner4
      case HandleType.TOP_RIGHT:
        return corners.corner3; // opposite of corner2 is corner3
      case HandleType.BOTTOM_LEFT:
        return corners.corner2; // opposite of corner3 is corner2
      case HandleType.BOTTOM_RIGHT:
        return corners.corner1; // opposite of corner4 is corner1
      default:
        return corners.corner1;
    }
  }

  private getDraggedCorner(corners: ScreenCorners, handle: HandleType): Point {
    switch (handle) {
      case HandleType.TOP_LEFT:
        return corners.corner1;
      case HandleType.TOP_RIGHT:
        return corners.corner2;
      case HandleType.BOTTOM_LEFT:
        return corners.corner3;
      case HandleType.BOTTOM_RIGHT:
        return corners.corner4;
      default:
        return corners.corner1;
    }
  }

  private distance(p1: Point, p2: Point): number {
    const dx = p1.x - p2.x;
    const dy = p1.y - p2.y;
    return Math.sqrt(dx * dx + dy * dy);
  }

  private scaleFromAnchor(
    corners: ScreenCorners,
    anchor: Point,
    scale: number
  ): ScreenCorners {
    return {
      corner1: this.scalePoint(corners.corner1, anchor, scale),
      corner2: this.scalePoint(corners.corner2, anchor, scale),
      corner3: this.scalePoint(corners.corner3, anchor, scale),
      corner4: this.scalePoint(corners.corner4, anchor, scale),
    };
  }

  private scalePoint(point: Point, anchor: Point, scale: number): Point {
    return {
      x: anchor.x + (point.x - anchor.x) * scale,
      y: anchor.y + (point.y - anchor.y) * scale,
    };
  }
}
