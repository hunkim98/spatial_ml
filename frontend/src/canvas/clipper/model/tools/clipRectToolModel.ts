import { IModel } from "../base";
import { HandleType, Point, Rect } from "../../types";

export interface ClipRectToolModelType {
  rect: Rect | null;
  activeHandle: HandleType | null;
  dragStart: Point | null;
  rectAtDragStart: Rect | null;
}

export class ClipRectToolModel
  extends IModel<ClipRectToolModelType>
  implements ClipRectToolModelType
{
  private _rect: Rect | null;
  private _activeHandle: HandleType | null = null;
  private _dragStart: Point | null;
  private _rectAtDragStart: Rect | null;

  constructor(props: Partial<ClipRectToolModelType>) {
    super();
    this._rect = props.rect ?? null;
    this._activeHandle = props.activeHandle ?? null;
    this._dragStart = props.dragStart ?? null;
    this._rectAtDragStart = props.rectAtDragStart ?? null;
  }

  get rect(): Rect | null {
    return this._rect;
  }

  get activeHandle(): HandleType | null {
    return this._activeHandle;
  }

  get dragStart(): Point | null {
    return this._dragStart;
  }

  get rectAtDragStart(): Rect | null {
    return this._rectAtDragStart;
  }

  set rect(rect: Rect | null) {
    this._rect = rect;
  }

  set activeHandle(activeHandle: HandleType | null) {
    this._activeHandle = activeHandle;
  }

  set dragStart(point: Point | null) {
    this._dragStart = point;
  }

  set rectAtDragStart(rect: Rect | null) {
    this._rectAtDragStart = rect;
  }

  reset() {
    this._rect = null;
    this._activeHandle = null;
    this._dragStart = null;
    this._rectAtDragStart = null;
  }
}
