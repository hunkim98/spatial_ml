import { Point, Rect } from "../types";

const HANDLE_HIT_RADIUS = 12;

export function isInsideRect(point: Point, rect: Rect): boolean {
  return (
    point.x >= rect.offset.x &&
    point.x <= rect.offset.x + rect.width &&
    point.y >= rect.offset.y &&
    point.y <= rect.offset.y + rect.height
  );
}

export function isNearPoint(p1: Point, p2: Point): boolean {
  const dx = p1.x - p2.x;
  const dy = p1.y - p2.y;

  return Math.sqrt(dx * dx + dy * dy) <= HANDLE_HIT_RADIUS;
}
