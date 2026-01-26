import { BaseController } from "./base";
import { CanvasModel } from "../model";
import { CanvasView } from "../view";
import { CanvasEvent, CanvasEventListeners } from "../events";
import { Point, HandleType, ScreenCorners, ScaleParams } from "../types";

type Models = Pick<CanvasModel, "transformModel">;
type Views = Pick<CanvasView, "imageLayerView" | "frameLayerView">;

export class ImageResizeController extends BaseController<
  Models,
  Views,
  ScaleParams
> {
  constructor(
    models: CanvasModel,
    views: CanvasView,
    listeners: CanvasEventListeners
  ) {
    super(models, views, listeners);
  }

  execute(params: ScaleParams): void {
    switch (params.type) {
      case "start":
        this.onScaleStart(params.point, params.handle);
        break;
      case "move":
        this.onScaleMove(params.point);
        break;
      case "end":
        this.onScaleEnd();
        break;
    }
  }

  private onScaleStart(point: Point, handle: HandleType): void {
    const { transformModel } = this.models;

    transformModel.activeHandle = handle;
    transformModel.dragStart = point;
    transformModel.cornersAtDragStart = transformModel.corners
      ? { ...transformModel.corners }
      : null;
  }

  private onScaleMove(point: Point): void {
    const { transformModel } = this.models;
    const { dragStart, cornersAtDragStart, activeHandle } = transformModel;

    if (!dragStart || !cornersAtDragStart || activeHandle === HandleType.NONE) {
      return;
    }

    // Get anchor (opposite corner)
    const anchor = this.getAnchorPoint(cornersAtDragStart, activeHandle);
    const draggedCorner = this.getDraggedCorner(cornersAtDragStart, activeHandle);

    // Calculate scale factor based on distance from anchor
    const originalDist = this.distance(draggedCorner, anchor);
    const newDist = this.distance(point, anchor);
    const scale = newDist / originalDist;

    // Apply scale from anchor point
    transformModel.corners = this.scaleFromAnchor(
      cornersAtDragStart,
      anchor,
      scale
    );

    this.dispatchEvent(CanvasEvent.TRANSFORM_CHANGED);
  }

  private onScaleEnd(): void {
    const { transformModel } = this.models;

    transformModel.activeHandle = HandleType.NONE;
    transformModel.dragStart = null;
    transformModel.cornersAtDragStart = null;
  }

  private getAnchorPoint(corners: ScreenCorners, handle: HandleType): Point {
    switch (handle) {
      case HandleType.TOP_LEFT:
        return corners.bottomRight;
      case HandleType.TOP_RIGHT:
        return corners.bottomLeft;
      case HandleType.BOTTOM_RIGHT:
        return corners.topLeft;
      case HandleType.BOTTOM_LEFT:
        return corners.topRight;
      default:
        return corners.topLeft;
    }
  }

  private getDraggedCorner(corners: ScreenCorners, handle: HandleType): Point {
    switch (handle) {
      case HandleType.TOP_LEFT:
        return corners.topLeft;
      case HandleType.TOP_RIGHT:
        return corners.topRight;
      case HandleType.BOTTOM_RIGHT:
        return corners.bottomRight;
      case HandleType.BOTTOM_LEFT:
        return corners.bottomLeft;
      default:
        return corners.topLeft;
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
      topLeft: this.scalePoint(corners.topLeft, anchor, scale),
      topRight: this.scalePoint(corners.topRight, anchor, scale),
      bottomRight: this.scalePoint(corners.bottomRight, anchor, scale),
      bottomLeft: this.scalePoint(corners.bottomLeft, anchor, scale),
    };
  }

  private scalePoint(point: Point, anchor: Point, scale: number): Point {
    return {
      x: anchor.x + (point.x - anchor.x) * scale,
      y: anchor.y + (point.y - anchor.y) * scale,
    };
  }
}
