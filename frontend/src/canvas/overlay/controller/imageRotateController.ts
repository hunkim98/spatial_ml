import { BaseController } from "./base";
import { CanvasModel } from "../model";
import { CanvasView } from "../view";
import { CanvasEvent, CanvasEventListeners } from "../events";
import { Point, ScreenCorners, RotateParams } from "../types";

type Models = Pick<CanvasModel, "transformModel">;
type Views = Pick<CanvasView, "imageLayerView" | "frameLayerView">;

export class ImageRotateController extends BaseController<
  Models,
  Views,
  RotateParams
> {
  constructor(
    models: CanvasModel,
    views: CanvasView,
    listeners: CanvasEventListeners
  ) {
    super(models, views, listeners);
  }

  execute(params: RotateParams): void {
    switch (params.type) {
      case "start":
        this.onRotateStart(params.point);
        break;
      case "move":
        this.onRotateMove(params.point);
        break;
      case "end":
        this.onRotateEnd();
        break;
    }
  }

  private onRotateStart(point: Point): void {
    const { transformModel } = this.models;

    transformModel.dragStart = point;
    transformModel.cornersAtDragStart = transformModel.corners
      ? { ...transformModel.corners }
      : null;
  }

  private onRotateMove(point: Point): void {
    const { transformModel } = this.models;
    const { dragStart, cornersAtDragStart } = transformModel;

    if (!dragStart || !cornersAtDragStart) return;

    const center = this.getCenter(cornersAtDragStart);

    // Calculate angle from center to drag start
    const startAngle = Math.atan2(
      dragStart.y - center.y,
      dragStart.x - center.x
    );

    // Calculate angle from center to current point
    const currentAngle = Math.atan2(
      point.y - center.y,
      point.x - center.x
    );

    // Rotation delta
    const deltaAngle = currentAngle - startAngle;

    // Rotate all corners around center
    transformModel.corners = this.rotateCorners(
      cornersAtDragStart,
      center,
      deltaAngle
    );

    this.dispatchEvent(CanvasEvent.TRANSFORM_CHANGED);
  }

  private onRotateEnd(): void {
    const { transformModel } = this.models;

    transformModel.dragStart = null;
    transformModel.cornersAtDragStart = null;
  }

  private getCenter(corners: ScreenCorners): Point {
    return {
      x: (corners.topLeft.x + corners.topRight.x + corners.bottomRight.x + corners.bottomLeft.x) / 4,
      y: (corners.topLeft.y + corners.topRight.y + corners.bottomRight.y + corners.bottomLeft.y) / 4,
    };
  }

  private rotateCorners(
    corners: ScreenCorners,
    center: Point,
    angle: number
  ): ScreenCorners {
    return {
      topLeft: this.rotatePoint(corners.topLeft, center, angle),
      topRight: this.rotatePoint(corners.topRight, center, angle),
      bottomRight: this.rotatePoint(corners.bottomRight, center, angle),
      bottomLeft: this.rotatePoint(corners.bottomLeft, center, angle),
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
