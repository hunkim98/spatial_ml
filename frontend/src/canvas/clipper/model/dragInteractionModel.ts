import { IModel } from "./base";
import { Point } from "../types/geometry";

export type DragInteractionModelType = {};

export class DragInteractionModel
  extends IModel<DragInteractionModelType>
  implements DragInteractionModelType
{
  private _dragStartWorldPosition: Point | null;
  private _lastDragScreenPosition: Point | null;

  constructor(props: Partial<DragInteractionModelType>) {
    super();
    this._dragStartWorldPosition = null;
    this._lastDragScreenPosition = null;
  }

  get dragStartWorldPosition(): Point | null {
    return this._dragStartWorldPosition;
  }

  set dragStartWorldPosition(point: Point | null) {
    this._dragStartWorldPosition = point;
  }
  get lastDragScreenPosition(): Point | null {
    return this._lastDragScreenPosition;
  }
  set lastDragScreenPosition(point: Point | null) {
    this._lastDragScreenPosition = point;
  }

  reset(): void {
    this._dragStartWorldPosition = null;
    this._lastDragScreenPosition = null;
  }
}
