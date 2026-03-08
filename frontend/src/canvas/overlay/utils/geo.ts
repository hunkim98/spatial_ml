import { GeoCorners, HandleType } from "../types";

function distanceGeo(
  a: { lng: number; lat: number },
  b: { lng: number; lat: number }
): number {
  const dlng = a.lng - b.lng;
  const dlat = a.lat - b.lat;
  return Math.sqrt(dlng * dlng + dlat * dlat);
}

function isInsideGeoPolygon(
  point: { lng: number; lat: number },
  corners: GeoCorners
): boolean {
  const polygon = [
    corners.corner1,
    corners.corner2,
    corners.corner4,
    corners.corner3,
  ];
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].lng,
      yi = polygon[i].lat;
    const xj = polygon[j].lng,
      yj = polygon[j].lat;
    const intersect =
      yi > point.lat !== yj > point.lat &&
      point.lng < ((xj - xi) * (point.lat - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

/**
 * Compute a hit radius in geo degrees based on the image size.
 * Uses a fraction of the diagonal so it scales with zoom level.
 */
function getGeoHitRadius(corners: GeoCorners): number {
  const diagonal = distanceGeo(corners.corner1, corners.corner4);
  return diagonal * 0.05;
}

/**
 * Detect which handle (if any) the point is near in geo space.
 * Mirrors toolManagerController.detectHandle() but for {lng, lat}.
 */
export function detectGeoHandle(
  point: { lng: number; lat: number },
  corners: GeoCorners
): HandleType {
  const hitRadius = getGeoHitRadius(corners);

  // Check corner handles first (they have priority)
  if (distanceGeo(point, corners.corner1) <= hitRadius)
    return HandleType.TOP_LEFT;
  if (distanceGeo(point, corners.corner2) <= hitRadius)
    return HandleType.TOP_RIGHT;
  if (distanceGeo(point, corners.corner4) <= hitRadius)
    return HandleType.BOTTOM_RIGHT;
  if (distanceGeo(point, corners.corner3) <= hitRadius)
    return HandleType.BOTTOM_LEFT;

  // Check if inside the polygon (body)
  if (isInsideGeoPolygon(point, corners)) return HandleType.BODY;

  return HandleType.NONE;
}
