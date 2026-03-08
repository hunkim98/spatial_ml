import { IModel } from "../base";
import { HandleType, ScreenCorners, GeoCorners } from "../../types";

export interface ImageTransformToolModelType {
  // Transform data (like clipRectToolModel stores corners)
  corners: ScreenCorners | null;
  geoCorners: GeoCorners | null;

  // Tool state
  isCreating: boolean;
  isEditing: boolean;
  activeHandle: HandleType | null;
  candidateHandle: HandleType | null;

  // Temporary state for transforms
  initialCorners: ScreenCorners | null;
}

/**
 * ImageTransformToolModel - stores image transform data and tool state
 * Following clipper editor's clipRectToolModel pattern (single source of truth)
 */
export class ImageTransformToolModel
  extends IModel<ImageTransformToolModelType>
  implements ImageTransformToolModelType
{
  private _corners: ScreenCorners | null;
  private _geoCorners: GeoCorners | null;
  private _isCreating: boolean;
  private _isEditing: boolean;
  private _activeHandle: HandleType | null;
  private _candidateHandle: HandleType | null;
  private _initialCorners: ScreenCorners | null;

  constructor(props: Partial<ImageTransformToolModelType>) {
    super();
    this._corners = props.corners ?? null;
    this._geoCorners = props.geoCorners ?? null;
    this._isCreating = props.isCreating ?? false;
    this._isEditing = props.isEditing ?? false;
    this._activeHandle = props.activeHandle ?? null;
    this._candidateHandle = props.candidateHandle ?? null;
    this._initialCorners = props.initialCorners ?? null;
  }

  get corners(): ScreenCorners | null {
    return this._corners;
  }
  set corners(value: ScreenCorners | null) {
    this._corners = value;
  }

  get geoCorners(): GeoCorners | null {
    return this._geoCorners;
  }
  set geoCorners(value: GeoCorners | null) {
    this._geoCorners = value;
  }

  get isCreating(): boolean {
    return this._isCreating;
  }
  set isCreating(value: boolean) {
    this._isCreating = value;
  }

  get isEditing(): boolean {
    return this._isEditing;
  }
  set isEditing(value: boolean) {
    this._isEditing = value;
  }

  get activeHandle(): HandleType | null {
    return this._activeHandle;
  }
  set activeHandle(handle: HandleType | null) {
    this._activeHandle = handle;
  }

  get candidateHandle(): HandleType | null {
    return this._candidateHandle;
  }
  set candidateHandle(handle: HandleType | null) {
    this._candidateHandle = handle;
  }

  get initialCorners(): ScreenCorners | null {
    return this._initialCorners;
  }
  set initialCorners(corners: ScreenCorners | null) {
    this._initialCorners = corners;
  }

  reset() {
    this._corners = null;
    this._geoCorners = null;
    this._isCreating = false;
    this._isEditing = false;
    this._activeHandle = null;
    this._candidateHandle = null;
    this._initialCorners = null;
  }
}
