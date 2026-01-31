import { ClipRect, HandleType } from "../types/clipRect";
import { Point } from "../types/geometry";
import { BaseService } from "./base";

const HANDLE_HIT_RADIUS = 12;

export class HitTestService extends BaseService {
  // No need for constructor since we only use static methods

  static detectHandleType(point: Point, rect?: ClipRect): HandleType {
    if (!rect) return HandleType.NONE;

    // Calculate corner positions
    const topLeft: Point = { x: rect.offset.x, y: rect.offset.y };
    const topRight: Point = { x: rect.offset.x + rect.width, y: rect.offset.y };
    const bottomRight: Point = {
      x: rect.offset.x + rect.width,
      y: rect.offset.y + rect.height,
    };
    const bottomLeft: Point = {
      x: rect.offset.x,
      y: rect.offset.y + rect.height,
    };
    const left: Point = {
      x: rect.offset.x,
      y: rect.offset.y + rect.height / 2,
    };
    const right: Point = {
      x: rect.offset.x + rect.width,
      y: rect.offset.y + rect.height / 2,
    };
    const top: Point = { x: rect.offset.x + rect.width / 2, y: rect.offset.y };
    const bottom: Point = {
      x: rect.offset.x + rect.width / 2,
      y: rect.offset.y + rect.height,
    };

    // Check corner handles first (they have priority)
    if (this.isNearPoint(point, topLeft)) return HandleType.TOP_LEFT;
    if (this.isNearPoint(point, topRight)) return HandleType.TOP_RIGHT;
    if (this.isNearPoint(point, bottomRight)) return HandleType.BOTTOM_RIGHT;
    if (this.isNearPoint(point, bottomLeft)) return HandleType.BOTTOM_LEFT;
    if (this.isNearPoint(point, left)) return HandleType.LEFT;
    if (this.isNearPoint(point, right)) return HandleType.RIGHT;
    if (this.isNearPoint(point, top)) return HandleType.TOP;
    if (this.isNearPoint(point, bottom)) return HandleType.BOTTOM;

    // Check if inside the rectangle
    if (this.isInsideRect(point, rect)) return HandleType.BODY;

    return HandleType.NONE;
  }

  static isNearPoint(p1: Point, p2: Point): boolean {
    const dx = p1.x - p2.x;
    const dy = p1.y - p2.y;

    return Math.sqrt(dx * dx + dy * dy) <= HANDLE_HIT_RADIUS;
  }

  static isInsideRect(point: Point, rect: ClipRect): boolean {
    return (
      point.x >= rect.offset.x &&
      point.x <= rect.offset.x + rect.width &&
      point.y >= rect.offset.y &&
      point.y <= rect.offset.y + rect.height
    );
  }
}
