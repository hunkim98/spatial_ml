import { IModel } from "../base";
import { HandleType, Point, Rect } from "../../types";

export interface ClipRectToolModelType {
  corner1: Point | null;
  corner2: Point | null;
  corner3: Point | null;
  corner4: Point | null;
}

export class ClipRectToolModel
  extends IModel<ClipRectToolModelType>
  implements ClipRectToolModelType
{
  private _corner1: Point | null;
  private _corner2: Point | null;
  private _corner3: Point | null;
  private _corner4: Point | null;
  private _activeHandle: HandleType | null;
  private _isCreating: boolean;

  constructor(props: Partial<ClipRectToolModelType>) {
    super();
    this._corner1 = props.corner1 ?? null;
    this._corner2 = props.corner2 ?? null;
    this._corner3 = props.corner3 ?? null;
    this._corner4 = props.corner4 ?? null;
    this._activeHandle = null;
    this._isCreating = false;
  }

  get corner1(): Point | null {
    return this._corner1;
  }
  get corner2(): Point | null {
    return this._corner2;
  }
  get corner3(): Point | null {
    return this._corner3;
  }
  get corner4(): Point | null {
    return this._corner4;
  }

  set corner1(point: Point | null) {
    this._corner1 = point;
  }
  set corner2(point: Point | null) {
    this._corner2 = point;
  }
  set corner3(point: Point | null) {
    this._corner3 = point;
  }
  set corner4(point: Point | null) {
    this._corner4 = point;
  }

  get activeHandle(): HandleType | null {
    return this._activeHandle;
  }
  set activeHandle(handle: HandleType | null) {
    this._activeHandle = handle;
  }

  get isCreating(): boolean {
    return this._isCreating;
  }
  set isCreating(value: boolean) {
    this._isCreating = value;
  }

  /** Computed Rect from the 4 corners. Returns null if corner1 or corner4 are unset. */
  get rect(): Rect | null {
    if (!this._corner1 || !this._corner4) return null;
    const minX = Math.min(this._corner1.x, this._corner4.x);
    const minY = Math.min(this._corner1.y, this._corner4.y);
    const maxX = Math.max(this._corner1.x, this._corner4.x);
    const maxY = Math.max(this._corner1.y, this._corner4.y);
    return {
      offset: { x: minX, y: minY },
      width: maxX - minX,
      height: maxY - minY,
    };
  }

  reset() {
    this._corner1 = null;
    this._corner2 = null;
    this._corner3 = null;
    this._corner4 = null;
    this._activeHandle = null;
    this._isCreating = false;
  }
}
