import { IModel } from "../base";
import { Location, Point, VertexRef, EdgeRef } from "../../types";

/** Pre-projected screen coordinates for a single polygon ring */
export interface ProjectedRing {
  points: Point[]; // screen-space vertices (excludes closure duplicate)
}

/** Pre-projected screen coordinates for a single feature */
export interface ProjectedFeature {
  rings: ProjectedRing[];
}

export interface GeoJSONEditModelType {
  featureCollection: GeoJSON.FeatureCollection | null;
  projectedFeatures: ProjectedFeature[];
  selectedFeatureIndex: number | null;
  activeVertex: VertexRef | null;
  candidateVertex: VertexRef | null;
  candidateEdge: EdgeRef | null;
  isEditing: boolean;
  initialPolygonCoords: number[][][] | null;
  mouseDownGeoPosition: Location | null;
  mouseMoveGeoPosition: Location | null;
}

export class GeoJSONEditModel
  extends IModel<GeoJSONEditModelType>
  implements GeoJSONEditModelType
{
  private _featureCollection: GeoJSON.FeatureCollection | null;
  private _projectedFeatures: ProjectedFeature[];
  private _selectedFeatureIndex: number | null;
  private _activeVertex: VertexRef | null;
  private _candidateVertex: VertexRef | null;
  private _candidateEdge: EdgeRef | null;
  private _isEditing: boolean;
  private _initialPolygonCoords: number[][][] | null;
  private _mouseDownGeoPosition: Location | null;
  private _mouseMoveGeoPosition: Location | null;

  constructor(props: Partial<GeoJSONEditModelType> = {}) {
    super();
    this._featureCollection = props.featureCollection ?? null;
    this._projectedFeatures = props.projectedFeatures ?? [];
    this._selectedFeatureIndex = props.selectedFeatureIndex ?? null;
    this._activeVertex = props.activeVertex ?? null;
    this._candidateVertex = props.candidateVertex ?? null;
    this._candidateEdge = props.candidateEdge ?? null;
    this._isEditing = props.isEditing ?? false;
    this._initialPolygonCoords = props.initialPolygonCoords ?? null;
    this._mouseDownGeoPosition = props.mouseDownGeoPosition ?? null;
    this._mouseMoveGeoPosition = props.mouseMoveGeoPosition ?? null;
  }

  get featureCollection() {
    return this._featureCollection;
  }
  set featureCollection(value: GeoJSON.FeatureCollection | null) {
    this._featureCollection = value;
  }

  get projectedFeatures() {
    return this._projectedFeatures;
  }
  set projectedFeatures(value: ProjectedFeature[]) {
    this._projectedFeatures = value;
  }

  get selectedFeatureIndex() {
    return this._selectedFeatureIndex;
  }
  set selectedFeatureIndex(value: number | null) {
    this._selectedFeatureIndex = value;
  }

  get activeVertex() {
    return this._activeVertex;
  }
  set activeVertex(value: VertexRef | null) {
    this._activeVertex = value;
  }

  get candidateVertex() {
    return this._candidateVertex;
  }
  set candidateVertex(value: VertexRef | null) {
    this._candidateVertex = value;
  }

  get candidateEdge() {
    return this._candidateEdge;
  }
  set candidateEdge(value: EdgeRef | null) {
    this._candidateEdge = value;
  }

  get isEditing() {
    return this._isEditing;
  }
  set isEditing(value: boolean) {
    this._isEditing = value;
  }

  get initialPolygonCoords() {
    return this._initialPolygonCoords;
  }
  set initialPolygonCoords(value: number[][][] | null) {
    this._initialPolygonCoords = value;
  }

  get mouseDownGeoPosition() {
    return this._mouseDownGeoPosition;
  }
  set mouseDownGeoPosition(value: Location | null) {
    this._mouseDownGeoPosition = value;
  }

  get mouseMoveGeoPosition() {
    return this._mouseMoveGeoPosition;
  }
  set mouseMoveGeoPosition(value: Location | null) {
    this._mouseMoveGeoPosition = value;
  }

  // ---- Helpers (pure data access, no projection logic) ----

  /** Get the coordinates array for a Polygon feature */
  getFeatureCoords(featureIndex: number): number[][][] | null {
    const fc = this._featureCollection;
    if (!fc || featureIndex < 0 || featureIndex >= fc.features.length)
      return null;
    const geom = fc.features[featureIndex].geometry;
    if (geom.type !== "Polygon") return null;
    return (geom as GeoJSON.Polygon).coordinates;
  }

  /** Set a specific vertex in-place, keeping ring closure */
  setVertexGeo(ref: VertexRef, lng: number, lat: number): void {
    const coords = this.getFeatureCoords(ref.featureIndex);
    if (!coords || ref.ringIndex >= coords.length) return;
    const ring = coords[ref.ringIndex];
    if (ref.vertexIndex >= ring.length) return;
    ring[ref.vertexIndex] = [lng, lat];
    // Keep ring closed: first and last vertex must match
    if (ref.vertexIndex === 0) {
      ring[ring.length - 1] = [lng, lat];
    } else if (ref.vertexIndex === ring.length - 1) {
      ring[0] = [lng, lat];
    }
  }

  reset(): void {
    this._featureCollection = null;
    this._projectedFeatures = [];
    this._selectedFeatureIndex = null;
    this._activeVertex = null;
    this._candidateVertex = null;
    this._candidateEdge = null;
    this._isEditing = false;
    this._initialPolygonCoords = null;
    this._mouseDownGeoPosition = null;
    this._mouseMoveGeoPosition = null;
  }
}
