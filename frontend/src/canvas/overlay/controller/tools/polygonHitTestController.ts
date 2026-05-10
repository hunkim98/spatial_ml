import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { BaseController } from "../base";
import { CanvasEventListeners } from "../../events";
import { ToolType } from "../../model/tools/toolManagerModel";
import { Point, VertexRef, EdgeRef } from "../../types";

type Models = Pick<
  CanvasModel,
  | "toolManagerModel"
  | "geojsonEditModel"
  | "mouseInteractionModel"
  | "editorStateModel"
>;
type Views = never;
type ExecuteParams = {
  e: React.MouseEvent<Element>;
};

const VERTEX_HIT_RADIUS = 12;
const EDGE_HIT_DISTANCE = 8;

/**
 * PolygonHitTestController — detects polygon vertices, edges, and bodies
 * under the cursor using pre-projected screen coordinates from the model.
 * When GeoJSON is loaded, this takes over tool detection.
 */
export class PolygonHitTestController extends BaseController<
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

  execute(_params: ExecuteParams): void {
    const { featureCollection, projectedFeatures } =
      this.models.geojsonEditModel;
    if (!featureCollection || projectedFeatures.length === 0) return;

    // Don't re-detect while actively dragging
    if (this.models.geojsonEditModel.isEditing) return;

    const mousePos = this.models.mouseInteractionModel.mouseMoveScreenPosition;
    if (!mousePos) return;

    const selectedIdx = this.models.geojsonEditModel.selectedFeatureIndex;

    // 1. Check vertices of selected polygon first
    if (selectedIdx !== null) {
      const projected = projectedFeatures[selectedIdx];
      if (projected) {
        const vertexHit = this.detectVertexHit(mousePos, selectedIdx, projected);
        if (vertexHit) {
          this.models.geojsonEditModel.candidateVertex = vertexHit;
          this.models.geojsonEditModel.candidateEdge = null;
          this.models.toolManagerModel.candidateTool =
            ToolType.POLYGON_VERTEX_MOVE;
          this.models.toolManagerModel.activeTool =
            ToolType.POLYGON_VERTEX_MOVE;
          return;
        }

        // 2. Check edges of selected polygon
        const edgeHit = this.detectEdgeHit(mousePos, selectedIdx, projected);
        if (edgeHit) {
          this.models.geojsonEditModel.candidateVertex = null;
          this.models.geojsonEditModel.candidateEdge = edgeHit;
          this.models.toolManagerModel.candidateTool = ToolType.POLYGON_SELECT;
          this.models.toolManagerModel.activeTool = ToolType.POLYGON_SELECT;
          return;
        }
      }
    }

    // 3. Check if inside any polygon body
    const bodyHit = this.detectBodyHit(mousePos);
    if (bodyHit !== null) {
      this.models.geojsonEditModel.candidateVertex = null;
      this.models.geojsonEditModel.candidateEdge = null;
      if (bodyHit === selectedIdx) {
        this.models.toolManagerModel.candidateTool = ToolType.POLYGON_MOVE;
        this.models.toolManagerModel.activeTool = ToolType.POLYGON_MOVE;
      } else {
        this.models.toolManagerModel.candidateTool = ToolType.POLYGON_SELECT;
        this.models.toolManagerModel.activeTool = ToolType.POLYGON_SELECT;
      }
      return;
    }

    // 4. Nothing under cursor
    this.models.geojsonEditModel.candidateVertex = null;
    this.models.geojsonEditModel.candidateEdge = null;
    this.models.toolManagerModel.candidateTool = null;
    this.models.toolManagerModel.activeTool = null;
  }

  private detectVertexHit(
    mousePos: Point,
    featureIndex: number,
    projected: { rings: { points: Point[] }[] }
  ): VertexRef | null {
    let closest: { ref: VertexRef; dist: number } | null = null;

    for (let ri = 0; ri < projected.rings.length; ri++) {
      const pts = projected.rings[ri].points;
      for (let vi = 0; vi < pts.length; vi++) {
        const dist = Math.hypot(pts[vi].x - mousePos.x, pts[vi].y - mousePos.y);
        if (dist <= VERTEX_HIT_RADIUS) {
          if (!closest || dist < closest.dist) {
            closest = {
              ref: { featureIndex, ringIndex: ri, vertexIndex: vi },
              dist,
            };
          }
        }
      }
    }

    return closest?.ref ?? null;
  }

  private detectEdgeHit(
    mousePos: Point,
    featureIndex: number,
    projected: { rings: { points: Point[] }[] }
  ): EdgeRef | null {
    let closest: { ref: EdgeRef; dist: number } | null = null;

    for (let ri = 0; ri < projected.rings.length; ri++) {
      const pts = projected.rings[ri].points;
      for (let si = 0; si < pts.length; si++) {
        const a = pts[si];
        const b = pts[(si + 1) % pts.length];
        const dist = pointToSegmentDistance(mousePos, a, b);
        if (dist <= EDGE_HIT_DISTANCE) {
          if (!closest || dist < closest.dist) {
            closest = {
              ref: { featureIndex, ringIndex: ri, segmentIndex: si },
              dist,
            };
          }
        }
      }
    }

    return closest?.ref ?? null;
  }

  private detectBodyHit(mousePos: Point): number | null {
    const { projectedFeatures } = this.models.geojsonEditModel;

    // Check in reverse order so topmost polygon wins
    for (let fi = projectedFeatures.length - 1; fi >= 0; fi--) {
      const projected = projectedFeatures[fi];
      if (projected.rings.length === 0) continue;
      const exteriorPts = projected.rings[0].points;
      if (isPointInsidePolygon(mousePos, exteriorPts)) {
        return fi;
      }
    }

    return null;
  }
}

function pointToSegmentDistance(p: Point, a: Point, b: Point): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const lenSq = dx * dx + dy * dy;
  if (lenSq === 0) return Math.hypot(p.x - a.x, p.y - a.y);

  let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / lenSq;
  t = Math.max(0, Math.min(1, t));

  const projX = a.x + t * dx;
  const projY = a.y + t * dy;
  return Math.hypot(p.x - projX, p.y - projY);
}

function isPointInsidePolygon(point: Point, polygon: Point[]): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x;
    const yi = polygon[i].y;
    const xj = polygon[j].x;
    const yj = polygon[j].y;

    const intersect =
      yi > point.y !== yj > point.y &&
      point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}
