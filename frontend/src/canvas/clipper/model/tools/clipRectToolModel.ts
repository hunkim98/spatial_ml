import { IModel } from "../base";
import { ClipRect, HandleType, Point } from "../../types";

export interface ClipRectToolModelType {
  rect: ClipRect | null;
  activeHandle: HandleType;
  dragStart: Point | null;
  rectAtDragStart: ClipRect | null;
}

export class ClipRectToolModel
  extends IModel<ClipRectToolModelType>
  implements ClipRectToolModelType
{
  private _rect: ClipRect | null;
  private _activeHandle: HandleType;
  private _dragStart: Point | null;
  private _rectAtDragStart: ClipRect | null;

  constructor(props: Partial<ClipRectToolModelType>) {
    super();
    this._rect = props.rect ?? null;
    this._activeHandle = props.activeHandle ?? HandleType.NONE;
    this._dragStart = props.dragStart ?? null;
    this._rectAtDragStart = props.rectAtDragStart ?? null;
  }

  get rect(): ClipRect | null {
    return this._rect;
  }

  get activeHandle(): HandleType {
    return this._activeHandle;
  }

  get dragStart(): Point | null {
    return this._dragStart;
  }

  get rectAtDragStart(): ClipRect | null {
    return this._rectAtDragStart;
  }

  set rect(rect: ClipRect | null) {
    this._rect = rect;
  }

  set activeHandle(activeHandle: HandleType) {
    this._activeHandle = activeHandle;
  }

  set dragStart(point: Point | null) {
    this._dragStart = point;
  }

  set rectAtDragStart(rect: ClipRect | null) {
    this._rectAtDragStart = rect;
  }

  reset() {
    this._rect = null;
    this._activeHandle = HandleType.NONE;
    this._dragStart = null;
    this._rectAtDragStart = null;
  }
}
