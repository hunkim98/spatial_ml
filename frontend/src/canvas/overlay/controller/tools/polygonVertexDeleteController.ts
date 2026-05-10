import { BaseController } from "../base";
import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { CanvasEvent, CanvasEventListeners } from "../../events";
import { VertexRef } from "../../types";

type Models = Pick<CanvasModel, "geojsonEditModel">;
type Views = never;
type ExecuteParams = {
  vertexRef: VertexRef;
};

/**
 * PolygonVertexDeleteController — removes a vertex from a polygon ring.
 * Requires at least 3 unique vertices to keep a valid polygon.
 */
export class PolygonVertexDeleteController extends BaseController<
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
    const { vertexRef } = params;
    const model = this.models.geojsonEditModel;

    const coords = model.getFeatureCoords(vertexRef.featureIndex);
    if (!coords) return;

    const ring = coords[vertexRef.ringIndex];
    if (!ring) return;

    // A valid ring needs at least 4 coords (3 unique + closure)
    if (ring.length <= 4) return;

    ring.splice(vertexRef.vertexIndex, 1);

    // Fix ring closure
    if (vertexRef.vertexIndex === 0) {
      ring[ring.length - 1] = [...ring[0]];
    }

    model.activeVertex = null;
    model.candidateVertex = null;

    this.dispatchEvent(CanvasEvent.GEOJSON_CHANGED);
  }
}
