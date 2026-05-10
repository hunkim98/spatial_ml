import { BaseController } from "../base";
import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { CanvasEvent, CanvasEventListeners } from "../../events";

type Models = Pick<CanvasModel, "geojsonEditModel">;
type Views = never;
type ExecuteParams = void;

/**
 * PolygonVertexAddController — inserts a new vertex on the candidate edge
 * at the current mouse geo position (triggered by double-click).
 * Reads pre-computed geo position from the model (set by ProjectionController).
 */
export class PolygonVertexAddController extends BaseController<
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

  execute(): void {
    const model = this.models.geojsonEditModel;
    const { candidateEdge } = model;
    const geoPos = model.mouseMoveGeoPosition;
    if (!candidateEdge || !model.featureCollection || !geoPos) return;

    const coords = model.getFeatureCoords(candidateEdge.featureIndex);
    if (!coords) return;

    const ring = coords[candidateEdge.ringIndex];
    if (!ring) return;

    const insertIdx = candidateEdge.segmentIndex + 1;
    ring.splice(insertIdx, 0, [geoPos.lng, geoPos.lat]);

    model.selectedFeatureIndex = candidateEdge.featureIndex;
    model.candidateEdge = null;

    this.dispatchEvent(CanvasEvent.GEOJSON_CHANGED);
  }
}
