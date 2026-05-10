import { BaseController } from "../base";
import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { CanvasEventListeners } from "../../events";
import { Point } from "../../types";

type Models = Pick<CanvasModel, "geojsonEditModel" | "mouseInteractionModel">;
type Views = never;
type ExecuteParams = {
  e: React.MouseEvent<Element>;
};

/**
 * PolygonSelectController — handles selecting a polygon by clicking on its body.
 */
export class PolygonSelectController extends BaseController<
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
    }
  }

  private onMouseDownExecute(): void {
    const model = this.models.geojsonEditModel;
    model.activeVertex = null;

    const screenPos =
      this.models.mouseInteractionModel.mouseDownScreenPosition;
    if (!screenPos) return;

    const bodyHit = this.detectBodyHit(screenPos);
    model.selectedFeatureIndex = bodyHit;
  }

  private detectBodyHit(mousePos: Point): number | null {
    const { projectedFeatures } = this.models.geojsonEditModel;

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
