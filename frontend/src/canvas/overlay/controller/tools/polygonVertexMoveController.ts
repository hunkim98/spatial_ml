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
 * PolygonVertexMoveController — handles dragging a single vertex to reposition it.
 * Reads pre-computed geo positions from the model (set by ProjectionController).
 */
export class PolygonVertexMoveController extends BaseController<
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
    const candidateVertex = model.candidateVertex;
    if (!candidateVertex) return;

    model.activeVertex = { ...candidateVertex };
    model.isEditing = true;
  }

  private onMouseMoveExecute(): void {
    const model = this.models.geojsonEditModel;
    if (!model.isEditing) return;

    const activeVertex = model.activeVertex;
    const geoPos = model.mouseMoveGeoPosition;
    if (!activeVertex || !geoPos) return;

    model.setVertexGeo(activeVertex, geoPos.lng, geoPos.lat);
  }

  private onMouseUpExecute(): void {
    const model = this.models.geojsonEditModel;
    if (!model.isEditing) return;

    model.isEditing = false;
    this.dispatchEvent(CanvasEvent.GEOJSON_CHANGED);
  }
}
