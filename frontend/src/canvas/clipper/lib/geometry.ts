import { Point, Rect } from "../types";

// Screen-space hit radius in pixels (constant regardless of zoom)
const SCREEN_HIT_RADIUS = 12;

export function isInsideRect(point: Point, rect: Rect): boolean {
  return (
    point.x >= rect.offset.x &&
    point.x <= rect.offset.x + rect.width &&
    point.y >= rect.offset.y &&
    point.y <= rect.offset.y + rect.height
  );
}

/**
 * Check if two points are near each other
 * @param p1 - First point
 * @param p2 - Second point
 * @param radius - Hit radius (optional, defaults to screen-space radius)
 */
export function isNearPoint(
  p1: Point,
  p2: Point,
  radius: number = SCREEN_HIT_RADIUS
): boolean {
  const dx = p1.x - p2.x;
  const dy = p1.y - p2.y;

  return Math.sqrt(dx * dx + dy * dy) <= radius;
}

/**
 * Calculate world-space hit radius based on scale
 * When zoomed out (scale < 1), returns larger world-space radius
 * When zoomed in (scale > 1), returns smaller world-space radius
 * This keeps the hit area consistent in screen space
 */
export function getScaledHitRadius(scale: number): number {
  return SCREEN_HIT_RADIUS / scale;
}
