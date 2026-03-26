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
 * ImageResizeToolController - handles resizing the image by dragging corner/edge handles
 * Uses delta-based positioning so the image follows the mouse smoothly without jumping.
 */
export class ImageResizeToolController extends BaseController<
  Models,
  Views,
  ExecuteParams
> {
  private customAnchor: Point | null = null;

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

    this.models.imageTransformToolModel.isEditing = true;
    this.models.imageTransformToolModel.initialCorners = {
      corner1: { ...corners.corner1 },
      corner2: { ...corners.corner2 },
      corner3: { ...corners.corner3 },
      corner4: { ...corners.corner4 },
    };

    if (
      this.models.imageTransformToolModel.activeHandle ===
      HandleType.CUSTOM_ANCHOR
    ) {
      const pos = this.models.mouseInteractionModel.mouseDownWorldPosition;
      this.customAnchor = pos ? { ...pos } : null;
    } else {
      this.customAnchor = null;
    }
  }

  onMouseMoveExecute(): void {
    if (!this.models.imageTransformToolModel.isEditing) return;

    const { mouseMoveWorldPosition, mouseDownWorldPosition } =
      this.models.mouseInteractionModel;
    const initialCorners = this.models.imageTransformToolModel.initialCorners;
    const activeHandle = this.models.imageTransformToolModel.activeHandle;
    const { width: imageWidth, height: imageHeight } =
      this.models.imageBufferModel;

    if (
      !mouseMoveWorldPosition ||
      !mouseDownWorldPosition ||
      !initialCorners ||
      !activeHandle ||
      !imageWidth ||
      !imageHeight
    )
      return;

    // Delta from where the mouse was pressed to where it is now
    const delta: Point = {
      x: mouseMoveWorldPosition.x - mouseDownWorldPosition.x,
      y: mouseMoveWorldPosition.y - mouseDownWorldPosition.y,
    };

    if (activeHandle === HandleType.CUSTOM_ANCHOR) {
      this.resizeFromCustomAnchor(delta, initialCorners);
    } else if (this.isEdgeHandle(activeHandle)) {
      this.resizeFromEdge(delta, initialCorners, activeHandle);
    } else {
      this.resizeFromCorner(
        delta,
        initialCorners,
        activeHandle,
        imageWidth,
        imageHeight
      );
    }
  }

  onMouseUpExecute(): void {
    this.models.imageTransformToolModel.isEditing = false;
    this.models.imageTransformToolModel.initialCorners = null;
    this.customAnchor = null;
  }

  // ========== Resize strategies ==========

  private isEdgeHandle(handle: HandleType): boolean {
    return (
      handle === HandleType.TOP_EDGE ||
      handle === HandleType.RIGHT_EDGE ||
      handle === HandleType.BOTTOM_EDGE ||
      handle === HandleType.LEFT_EDGE
    );
  }

  /**
   * Corner resize: move the dragged corner by delta, then compute
   * new dimensions from anchor to virtual corner position.
   */
  private resizeFromCorner(
    delta: Point,
    initialCorners: ScreenCorners,
    handle: HandleType,
    imageWidth: number,
    imageHeight: number
  ): void {
    const aspectRatio = imageWidth / imageHeight;
    const anchor = this.getAnchorPoint(initialCorners, handle);
    const draggedCorner = this.getDraggedCorner(initialCorners, handle);

    // Virtual position = where the corner would be after applying delta
    const virtual: Point = {
      x: draggedCorner.x + delta.x,
      y: draggedCorner.y + delta.y,
    };

    let width = Math.abs(virtual.x - anchor.x);
    let height = Math.abs(virtual.y - anchor.y);

    // Constrain to aspect ratio
    if (width / aspectRatio > height) {
      height = width / aspectRatio;
    } else {
      width = height * aspectRatio;
    }

    const signX = virtual.x >= anchor.x ? 1 : -1;
    const signY = virtual.y >= anchor.y ? 1 : -1;

    const newCorners: ScreenCorners = {
      corner1: { x: 0, y: 0 },
      corner2: { x: 0, y: 0 },
      corner3: { x: 0, y: 0 },
      corner4: { x: 0, y: 0 },
    };

    if (signX > 0 && signY > 0) {
      newCorners.corner1 = anchor;
      newCorners.corner2 = { x: anchor.x + width, y: anchor.y };
      newCorners.corner3 = { x: anchor.x, y: anchor.y + height };
      newCorners.corner4 = { x: anchor.x + width, y: anchor.y + height };
    } else if (signX < 0 && signY > 0) {
      newCorners.corner1 = { x: anchor.x - width, y: anchor.y };
      newCorners.corner2 = anchor;
      newCorners.corner3 = { x: anchor.x - width, y: anchor.y + height };
      newCorners.corner4 = { x: anchor.x, y: anchor.y + height };
    } else if (signX > 0 && signY < 0) {
      newCorners.corner1 = { x: anchor.x, y: anchor.y - height };
      newCorners.corner2 = { x: anchor.x + width, y: anchor.y - height };
      newCorners.corner3 = anchor;
      newCorners.corner4 = { x: anchor.x + width, y: anchor.y };
    } else {
      newCorners.corner1 = { x: anchor.x - width, y: anchor.y - height };
      newCorners.corner2 = { x: anchor.x, y: anchor.y - height };
      newCorners.corner3 = { x: anchor.x - width, y: anchor.y };
      newCorners.corner4 = anchor;
    }

    this.models.imageTransformToolModel.corners = newCorners;
  }

  /**
   * Edge resize: move the edge midpoint by delta, compute scale
   * relative to the opposite edge, and scale uniformly from that anchor.
   */
  private resizeFromEdge(
    delta: Point,
    initialCorners: ScreenCorners,
    handle: HandleType
  ): void {
    const anchor = this.getAnchorPoint(initialCorners, handle);
    const draggedMidpoint = this.getDraggedEdgeMidpoint(
      initialCorners,
      handle
    );

    const initialDist = this.distance(anchor, draggedMidpoint);
    if (initialDist === 0) return;

    // Virtual midpoint = initial midpoint + delta
    const virtual: Point = {
      x: draggedMidpoint.x + delta.x,
      y: draggedMidpoint.y + delta.y,
    };

    // Project onto the perpendicular axis of the edge
    let currentDist: number;
    if (
      handle === HandleType.TOP_EDGE ||
      handle === HandleType.BOTTOM_EDGE
    ) {
      currentDist = Math.abs(virtual.y - anchor.y);
    } else {
      currentDist = Math.abs(virtual.x - anchor.x);
    }

    const scale = currentDist / initialDist;
    if (scale === 0) return;

    this.models.imageTransformToolModel.corners = this.scaleFromAnchor(
      initialCorners,
      anchor,
      scale
    );
  }

  /**
   * Custom anchor resize: anchor is the mouse-down position.
   * Move the farthest corner by delta and compute scale from anchor
   * to that virtual corner.
   */
  private resizeFromCustomAnchor(
    delta: Point,
    initialCorners: ScreenCorners
  ): void {
    if (!this.customAnchor) return;

    // Find the farthest corner from the anchor
    const corners = [
      initialCorners.corner1,
      initialCorners.corner2,
      initialCorners.corner3,
      initialCorners.corner4,
    ];
    let farthest = corners[0];
    let maxDist = 0;
    for (const c of corners) {
      const d = this.distance(this.customAnchor, c);
      if (d > maxDist) {
        maxDist = d;
        farthest = c;
      }
    }
    if (maxDist === 0) return;

    // Virtual farthest corner = initial farthest + delta
    const virtual: Point = {
      x: farthest.x + delta.x,
      y: farthest.y + delta.y,
    };
    const currentDist = this.distance(this.customAnchor, virtual);
    const scale = currentDist / maxDist;
    if (scale === 0) return;

    this.models.imageTransformToolModel.corners = this.scaleFromAnchor(
      initialCorners,
      this.customAnchor,
      scale
    );
  }

  // ========== Helpers ==========

  private getAnchorPoint(corners: ScreenCorners, handle: HandleType): Point {
    switch (handle) {
      case HandleType.TOP_LEFT:
        return corners.corner4;
      case HandleType.TOP_RIGHT:
        return corners.corner3;
      case HandleType.BOTTOM_LEFT:
        return corners.corner2;
      case HandleType.BOTTOM_RIGHT:
        return corners.corner1;
      case HandleType.TOP_EDGE:
        return this.midpoint(corners.corner3, corners.corner4);
      case HandleType.BOTTOM_EDGE:
        return this.midpoint(corners.corner1, corners.corner2);
      case HandleType.LEFT_EDGE:
        return this.midpoint(corners.corner2, corners.corner4);
      case HandleType.RIGHT_EDGE:
        return this.midpoint(corners.corner1, corners.corner3);
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

  private getDraggedEdgeMidpoint(
    corners: ScreenCorners,
    handle: HandleType
  ): Point {
    switch (handle) {
      case HandleType.TOP_EDGE:
        return this.midpoint(corners.corner1, corners.corner2);
      case HandleType.BOTTOM_EDGE:
        return this.midpoint(corners.corner3, corners.corner4);
      case HandleType.LEFT_EDGE:
        return this.midpoint(corners.corner1, corners.corner3);
      case HandleType.RIGHT_EDGE:
        return this.midpoint(corners.corner2, corners.corner4);
      default:
        return corners.corner1;
    }
  }

  private midpoint(a: Point, b: Point): Point {
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
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
