import { BaseController } from "./base";
import { CanvasModel } from "../model";
import { CanvasView } from "../view";
import { CanvasEventListeners } from "../events";
import { Point, HandleType } from "../types";

const HANDLE_HIT_RADIUS = 12;

type Models = Pick<CanvasModel, "transformModel">;
type Views = Pick<CanvasView, never>;

export class HitTestController extends BaseController<Models, Views, Point> {
  constructor(
    models: CanvasModel,
    views: CanvasView,
    listeners: CanvasEventListeners
  ) {
    super(models, views, listeners);
  }

  execute(point: Point): HandleType {
    const { corners } = this.models.transformModel;

    if (!corners) return HandleType.NONE;

    // Check corner handles first (they have priority)
    if (this.isNearPoint(point, corners.topLeft)) return HandleType.TOP_LEFT;
    if (this.isNearPoint(point, corners.topRight)) return HandleType.TOP_RIGHT;
    if (this.isNearPoint(point, corners.bottomRight)) return HandleType.BOTTOM_RIGHT;
    if (this.isNearPoint(point, corners.bottomLeft)) return HandleType.BOTTOM_LEFT;

    // Check if inside the polygon
    if (this.isInsidePolygon(point, corners)) return HandleType.BODY;

    return HandleType.NONE;
  }

  private isNearPoint(p1: Point, p2: Point): boolean {
    const dx = p1.x - p2.x;
    const dy = p1.y - p2.y;

    return Math.sqrt(dx * dx + dy * dy) <= HANDLE_HIT_RADIUS;
  }

  private isInsidePolygon(
    point: Point,
    corners: { topLeft: Point; topRight: Point; bottomRight: Point; bottomLeft: Point }
  ): boolean {
    const polygon = [
      corners.topLeft,
      corners.topRight,
      corners.bottomRight,
      corners.bottomLeft,
    ];

    let inside = false;
    const n = polygon.length;

    for (let i = 0, j = n - 1; i < n; j = i++) {
      const xi = polygon[i].x;
      const yi = polygon[i].y;
      const xj = polygon[j].x;
      const yj = polygon[j].y;

      if (
        yi > point.y !== yj > point.y &&
        point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi
      ) {
        inside = !inside;
      }
    }

    return inside;
  }
}
