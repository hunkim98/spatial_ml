import { IModel } from "./base";
import { Point } from "../types";

export type MouseInteractionModelType = {
  mouseDownWorldPosition: Point | null;
  mouseDownScreenPosition: Point | null;
  mouseMoveWorldPosition: Point | null;
  mouseMoveScreenPosition: Point | null;
  mouseUpWorldPosition: Point | null;
  mouseUpScreenPosition: Point | null;
};

/**
 * MouseInteractionModel - tracks mouse positions during interactions
 * Similar to clipper editor's MouseInteractionModel
 */
export class MouseInteractionModel
  extends IModel<MouseInteractionModelType>
  implements MouseInteractionModelType
{
  private _mouseDownWorldPosition: Point | null = null;
  private _mouseDownScreenPosition: Point | null = null;
  private _mouseMoveWorldPosition: Point | null = null;
  private _mouseMoveScreenPosition: Point | null = null;
  private _mouseUpWorldPosition: Point | null = null;
  private _mouseUpScreenPosition: Point | null = null;

  get mouseDownWorldPosition(): Point | null {
    return this._mouseDownWorldPosition;
  }
  set mouseDownWorldPosition(pos: Point | null) {
    this._mouseDownWorldPosition = pos;
  }

  get mouseDownScreenPosition(): Point | null {
    return this._mouseDownScreenPosition;
  }
  set mouseDownScreenPosition(pos: Point | null) {
    this._mouseDownScreenPosition = pos;
  }

  get mouseMoveWorldPosition(): Point | null {
    return this._mouseMoveWorldPosition;
  }
  set mouseMoveWorldPosition(pos: Point | null) {
    this._mouseMoveWorldPosition = pos;
  }

  get mouseMoveScreenPosition(): Point | null {
    return this._mouseMoveScreenPosition;
  }
  set mouseMoveScreenPosition(pos: Point | null) {
    this._mouseMoveScreenPosition = pos;
  }

  get mouseUpWorldPosition(): Point | null {
    return this._mouseUpWorldPosition;
  }
  set mouseUpWorldPosition(pos: Point | null) {
    this._mouseUpWorldPosition = pos;
  }

  get mouseUpScreenPosition(): Point | null {
    return this._mouseUpScreenPosition;
  }
  set mouseUpScreenPosition(pos: Point | null) {
    this._mouseUpScreenPosition = pos;
  }

  update(partial: Partial<MouseInteractionModelType>) {
    if (partial.mouseDownWorldPosition !== undefined)
      this._mouseDownWorldPosition = partial.mouseDownWorldPosition;
    if (partial.mouseDownScreenPosition !== undefined)
      this._mouseDownScreenPosition = partial.mouseDownScreenPosition;
    if (partial.mouseMoveWorldPosition !== undefined)
      this._mouseMoveWorldPosition = partial.mouseMoveWorldPosition;
    if (partial.mouseMoveScreenPosition !== undefined)
      this._mouseMoveScreenPosition = partial.mouseMoveScreenPosition;
    if (partial.mouseUpWorldPosition !== undefined)
      this._mouseUpWorldPosition = partial.mouseUpWorldPosition;
    if (partial.mouseUpScreenPosition !== undefined)
      this._mouseUpScreenPosition = partial.mouseUpScreenPosition;
  }

  reset() {
    this._mouseDownWorldPosition = null;
    this._mouseDownScreenPosition = null;
    this._mouseMoveWorldPosition = null;
    this._mouseMoveScreenPosition = null;
    this._mouseUpWorldPosition = null;
    this._mouseUpScreenPosition = null;
  }
}
