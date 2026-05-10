import { BaseController } from "../base";
import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { CanvasEvent, CanvasEventListeners } from "../../events";

type Models = Pick<CanvasModel, "geojsonEditModel">;
type Views = never;
type ExecuteParams = {
  featureIndex: number;
};

/**
 * PolygonDeleteController — removes an entire polygon feature from the collection.
 */
export class PolygonDeleteController extends BaseController<
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
    const { featureIndex } = params;
    const model = this.models.geojsonEditModel;

    if (!model.featureCollection) return;
    if (
      featureIndex < 0 ||
      featureIndex >= model.featureCollection.features.length
    )
      return;

    model.featureCollection.features.splice(featureIndex, 1);
    model.selectedFeatureIndex = null;
    model.activeVertex = null;
    model.candidateVertex = null;

    this.dispatchEvent(CanvasEvent.GEOJSON_CHANGED);
  }
}
