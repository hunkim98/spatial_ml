import { IModel } from "./base";
import { Point } from "../types/geometry";

export type DragInteractionModelType = {};

export class DragInteractionModel
  extends IModel<DragInteractionModelType>
  implements DragInteractionModelType
{
  private _dragStart: Point | null;
  private _lastDragScreenPoint: Point | null;

  constructor(props: Partial<DragInteractionModelType>) {
    super();
    this._dragStart = null;
    this._lastDragScreenPoint = null;
  }

  get dragStart(): Point | null {
    return this._dragStart;
  }

  set dragStart(point: Point | null) {
    this._dragStart = point;
  }
  get lastDragScreenPoint(): Point | null {
    return this._lastDragScreenPoint;
  }
  set lastDragScreenPoint(point: Point | null) {
    this._lastDragScreenPoint = point;
  }

  reset(): void {
    this._dragStart = null;
  }
}
