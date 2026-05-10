import { BaseController } from "../base";
import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { CanvasEvent, CanvasEventListeners } from "../../events";

type Models = Pick<
  CanvasModel,
  "geojsonEditModel" | "mouseInteractionModel"
>;
type Views = never;
type ExecuteParams = {
  e: React.MouseEvent<Element>;
};

/**
 * PolygonMoveController — handles translating an entire polygon by dragging.
 * Reads pre-computed geo positions from the model (set by ProjectionController).
 */
export class PolygonMoveController extends BaseController<
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
    } else if (e.type === "mousemove") {
      this.onMouseMoveExecute();
    } else if (e.type === "mouseup") {
      this.onMouseUpExecute();
    }
  }

  private onMouseDownExecute(): void {
    const model = this.models.geojsonEditModel;
    model.activeVertex = null;

    const selectedIdx = model.selectedFeatureIndex;
    if (selectedIdx === null) return;

    const coords = model.getFeatureCoords(selectedIdx);
    if (!coords) return;

    model.initialPolygonCoords = JSON.parse(JSON.stringify(coords));
    model.isEditing = true;
  }

  private onMouseMoveExecute(): void {
    const model = this.models.geojsonEditModel;
    if (!model.isEditing) return;

    const selectedIdx = model.selectedFeatureIndex;
    const initialCoords = model.initialPolygonCoords;
    const downGeo = model.mouseDownGeoPosition;
    const currGeo = model.mouseMoveGeoPosition;
    if (selectedIdx === null || !initialCoords || !downGeo || !currGeo) return;

    const dLng = currGeo.lng - downGeo.lng;
    const dLat = currGeo.lat - downGeo.lat;

    const feature = model.featureCollection!.features[selectedIdx];
    if (feature.geometry.type !== "Polygon") return;
    const coords = (feature.geometry as GeoJSON.Polygon).coordinates;

    for (let ri = 0; ri < coords.length; ri++) {
      for (let vi = 0; vi < coords[ri].length; vi++) {
        coords[ri][vi] = [
          initialCoords[ri][vi][0] + dLng,
          initialCoords[ri][vi][1] + dLat,
        ];
      }
    }
  }

  private onMouseUpExecute(): void {
    const model = this.models.geojsonEditModel;
    if (!model.isEditing) return;

    model.isEditing = false;
    model.initialPolygonCoords = null;
    this.dispatchEvent(CanvasEvent.GEOJSON_CHANGED);
  }
}
