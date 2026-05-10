import { BaseController } from "./base";
import { CanvasModel } from "../model";
import { CanvasView } from "../view";
import { CanvasEventListeners } from "../events";
import { Location, Point } from "../types";
import {
  ProjectedFeature,
  ProjectedRing,
} from "../model/tools/geojsonEditModel";

type Models = Pick<
  CanvasModel,
  "geojsonEditModel" | "mouseInteractionModel"
>;
type Views = never;
type ExecuteParams = void;

/**
 * ProjectionController — handles all geo ↔ screen coordinate conversion.
 *
 * - computeGeoPositions(): converts mouse screen positions to geo positions
 *   and stores them on the model (called before tool controllers).
 * - execute(): projects all GeoJSON features from geo to screen coordinates
 *   and writes the result to model.projectedFeatures (called during render).
 */
export class ProjectionController extends BaseController<
  Models,
  Views,
  ExecuteParams
> {
  private _project: ((lngLat: Location) => Point) | null = null;
  private _unproject: ((point: Point) => Location) | null = null;

  constructor(
    models: CanvasModel,
    views: CanvasView,
    listeners: CanvasEventListeners
  ) {
    super(models, views, listeners);
  }

  /** Bind to a MapLibre map's project/unproject functions */
  bind(
    project: (lngLat: Location) => Point,
    unproject: (point: Point) => Location
  ): void {
    this._project = project;
    this._unproject = unproject;
  }

  unbind(): void {
    this._project = null;
    this._unproject = null;
  }

  get isBound(): boolean {
    return this._project !== null && this._unproject !== null;
  }

  /**
   * Pre-compute geo positions from mouse screen positions.
   * Called by the Editor before tool controllers run.
   */
  computeGeoPositions(): void {
    if (!this._unproject) return;

    const mouse = this.models.mouseInteractionModel;
    const model = this.models.geojsonEditModel;

    const downScreen = mouse.mouseDownScreenPosition;
    model.mouseDownGeoPosition = downScreen
      ? this._unproject(downScreen)
      : null;

    const moveScreen = mouse.mouseMoveScreenPosition;
    model.mouseMoveGeoPosition = moveScreen
      ? this._unproject(moveScreen)
      : null;
  }

  /** Project all GeoJSON features to screen coordinates */
  execute(): void {
    const model = this.models.geojsonEditModel;
    if (!model.featureCollection || !this._project) {
      model.projectedFeatures = [];
      return;
    }

    const fc = model.featureCollection;
    const projected: ProjectedFeature[] = [];

    for (const feature of fc.features) {
      if (feature.geometry.type !== "Polygon") {
        projected.push({ rings: [] });
        continue;
      }

      const coords = (feature.geometry as GeoJSON.Polygon).coordinates;
      const rings: ProjectedRing[] = [];

      for (const ring of coords) {
        // Skip last vertex (GeoJSON closure duplicate)
        const vertexCount = ring.length > 1 ? ring.length - 1 : ring.length;
        const points: Point[] = [];

        for (let vi = 0; vi < vertexCount; vi++) {
          points.push(
            this._project({ lng: ring[vi][0], lat: ring[vi][1] })
          );
        }

        rings.push({ points });
      }

      projected.push({ rings });
    }

    model.projectedFeatures = projected;
  }
}
